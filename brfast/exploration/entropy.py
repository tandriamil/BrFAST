#!/usr/bin/python3
"""Module containing the entropy-based exploration algorithm."""

import importlib
from datetime import datetime
from math import ceil
from multiprocessing import Pool
from os import cpu_count
from typing import Dict

from loguru import logger

from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.exploration import Exploration, State, TraceData
from brfast.measures.distinguishability.entropy import attribute_set_entropy
from brfast.utils.sequences import sort_dict_by_value

pd = importlib.import_module(params.get('DataAnalysis', 'engine'))


class Entropy(Exploration):
    """The implementation of the entropy-based exploration algorithm."""

    def _search_for_solution(self):
        """Search for a solution using the entropy-based exploration algorithm.

        This function has to
        - Set the best solution currently found (AttributeSet).
        - Update the set of the attribute sets that satisfy the sensitivity
          threshold (Set[AttributeSet]).
        - Update the list of the explored attributes which is the trace of the
          execution. The information regarding an explored attribute is stored
          as a dictionary with the following key/values:
          * time (float): The time spent since the starting of the exploration
                          in seconds (use timedelta.total_seconds()).
          * attributes (Set[int]): The set of the ids of the attributes.
          * sensitivity (float): The sensitivity of the attribute set.
          * usability_cost (float): The usability cost of the attribute set.
          * cost_explanation (Dict[str: float]): The explanation of the cost of
                                                 the attribute set.
          * state (State): The state of this attribute set (see State class).
        - Log the explored attribute sets for debugging purposes using loguru.

        Note:
            We use the ids of the attributes instead of their name to reduce
            the size of the trace in memory and when saved in json format.
        """
        # Get a dictionary of the entropy of each attribute
        logger.info('Computing the entropy of each attribute...')
        attributes_entropy = get_attributes_entropy(
            self._dataset, self._dataset.candidate_attributes)
        entropy_compute_time = datetime.now() - self._start_time
        logger.info('Entropy of the attributes computed after '
                    f'{entropy_compute_time}.')

        # Take the attributes in the order of their entropy
        attribute_set = AttributeSet()
        for attribute, _ in sort_dict_by_value(attributes_entropy,
                                               reverse=True):

            # Check the new attribute set that is obtained
            attribute_set.add(attribute)
            logger.debug(f'Exploring {attribute_set}...')

            # Compute its sensitivity and its cost
            sensitivity = self._sensitivity.evaluate(attribute_set)
            cost, cost_explanation = (
                self._usability_cost.evaluate(attribute_set))
            logger.debug(f'  Sensitivity ({sensitivity}), '
                         f'usability cost ({cost})')

            # If it satisfies the sensitivity threshold, quit the loop
            if sensitivity <= self._sensitivity_threshold:
                self._update_solution(attribute_set)
                self._add_satisfying_attribute_set(attribute_set)

                # Store this attribute set in the explored sets
                compute_time = str(datetime.now() - self._start_time)
                self._add_explored_attribute_set({
                    TraceData.TIME: compute_time,
                    TraceData.ATTRIBUTES: attribute_set.attribute_ids,
                    TraceData.SENSITIVITY: sensitivity,
                    TraceData.USABILITY_COST: cost,
                    TraceData.COST_EXPLANATION: cost_explanation,
                    TraceData.STATE: State.SATISFYING
                })

                # Quit the loop if we found a solution
                break

            # If it does not satisfy the sensitivity threshold, we continue
            compute_time = str(datetime.now() - self._start_time)
            self._add_explored_attribute_set({
                TraceData.TIME: compute_time,
                TraceData.ATTRIBUTES: attribute_set.attribute_ids,
                TraceData.SENSITIVITY: sensitivity,
                TraceData.USABILITY_COST: cost,
                TraceData.COST_EXPLANATION: cost_explanation,
                TraceData.STATE: State.EXPLORED
            })


def get_attributes_entropy(dataset: FingerprintDataset,
                           attributes: AttributeSet
                           ) -> Dict[Attribute, float]:
    """Give a dictionary with the entropy of each attribute.

    Args:
        dataset: The fingerprint dataset used to compute the entropy.
        attributes: The attributes for which we compute the entropy.

    Raises:
        ValueError: There are attributes and the fingerprint dataset is empty.
        KeyError: An attribute is not in the fingerprint dataset.

    Returns:
        A dictionary with each attribute (Attribute) and its entropy.
    """
    # Some checks before starting the exploration
    if attributes and dataset.dataframe.empty:
        raise ValueError('Cannot compute the entropy on an empty dataset.')
    for attribute in attributes:
        if attribute not in dataset.candidate_attributes:
            raise KeyError(f'The attribute {attribute} is not in the dataset.')

    # We will work on a dataset with only a fingerprint per browser to avoid
    # over-counting effects
    df_one_fp_per_browser = dataset.get_df_w_one_fp_per_browser()

    # If we execute on a single process
    if not params.getboolean('Multiprocessing', 'explorations'):
        logger.debug('Measuring the attributes entropy on a single process...')
        return compute_attribute_entropy(df_one_fp_per_browser, attributes)

    # The dictionary to update when using multiprocessing
    logger.debug('Measuring the attributes entropy using multiprocessing...')
    attributes_entropy = {}

    # Infer the number of cores to use
    free_cores = params.getint('Multiprocessing', 'free_cores')
    nb_cores = max(cpu_count() - free_cores, 1)
    attributes_per_core = int(ceil(len(attributes)/nb_cores))
    logger.debug(f'Sharing {len(attributes)} attributes over '
                 f'{nb_cores}(+{free_cores}) cores, hence '
                 f'{attributes_per_core} attributes per core.')

    def update_attributes_entropy(attrs_entropy: Dict[Attribute, float]):
        """Update the complete dictionary attributes_entropy.

        Args:
            attrs_entropy: The dictionary containing the subset of the results
                           computed by a process.

        Note: This is executed by the main thread and does not pose any
              concurrency or synchronization problem.
        """
        for _attribute, _attribute_entropy in attrs_entropy.items():
            attributes_entropy[_attribute] = _attribute_entropy

    # Spawn a number of processes equal to the number of cores
    attributes_list = list(attributes)
    async_results = []
    with Pool(processes=nb_cores) as pool:
        for process_id in range(nb_cores):
            # Generate the candidate attributes for this process
            start_id = process_id * attributes_per_core
            end_id = (process_id + 1) * attributes_per_core
            attributes_subset = AttributeSet(attributes_list[start_id:end_id])

            async_result = pool.apply_async(
                compute_attribute_entropy,
                args=(df_one_fp_per_browser, attributes_subset),
                callback=update_attributes_entropy)
            async_results.append(async_result)

        # Wait for all the processes to finish (otherwise we would exit
        # before collecting their result)
        for async_result in async_results:
            async_result.wait()

    return attributes_entropy


def compute_attribute_entropy(df_one_fp_per_browser: pd.DataFrame,
                              attributes_subset: AttributeSet
                              ) -> Dict[Attribute, float]:
    """Compute the entropy of each attribute (passed to each process).

    Args:
        df_one_fp_per_browser: The dataframe with only one fingerprint per
                               browser.
        attributes_subset: The attributes for which to compute the entropy.

    Returns:
        A dictionary mapping each attribute to its entropy.
    """
    attributes_entropy = {}

    for attribute in attributes_subset:
        attributes_entropy[attribute] = attribute_set_entropy(
            df_one_fp_per_browser, AttributeSet([attribute]))

    return attributes_entropy
