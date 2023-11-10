#!/usr/bin/python3
"""Module containing the exploration algorithm based on conditional entropy."""

import importlib
from datetime import datetime
from math import ceil
from multiprocessing import Pool
from os import cpu_count
from typing import Tuple

from loguru import logger

from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.exploration import Exploration, State, TraceData
from brfast.measures.distinguishability.entropy import attribute_set_entropy

pd = importlib.import_module(params.get('DataAnalysis', 'engine'))


def get_best_conditional_entropic_attribute(dataset: FingerprintDataset,
                                            current_attributes: AttributeSet,
                                            candidate_attributes: AttributeSet
                                            ) -> Attribute:
    """Get the attribute that provides the highest total entropy.

    When several attributes provide the same total entropy, the attribute of
    the lowest id is given. If no attribute increases the total entropy, we
    still provide the attribute of the lowest id.

    Args:
        dataset: The dataset used to compute the conditional entropy.
        current_attributes: The attributes that compose the current solution.
        candidate_attributes: The candidate attributes (i.e., those available).

    Raises:
        ValueError: There are candidate attributes and the fingerprint dataset
                    is empty.
        KeyError: One of the candidate attributes is not in the fingerprint
                  dataset.

    Returns:
        The attribute that has the highest conditional entropy among the
        candidate attributes and that is not part of the current attributes.
    """
    logger.debug('Getting the best conditional entropic attribute from '
                 f'{current_attributes}...')

    # Some checks before starting the exploration
    if candidate_attributes and dataset.dataframe.empty:
        raise ValueError('Cannot compute the conditional entropy on an empty '
                         'dataset.')
    for attribute in candidate_attributes:
        if attribute not in dataset.candidate_attributes:
            raise KeyError(f'The attribute {attribute} is not in the dataset.')

    # We will work on a dataset with only a fingerprint per browser to avoid
    # over-counting effects
    df_one_fp_per_browser = dataset.get_df_w_one_fp_per_browser()

    # If we execute on a single process
    if not params.getboolean('Multiprocessing', 'explorations'):
        logger.debug('Measuring the attributes entropy on a single process...')
        best_attribute, best_total_ent = best_conditional_entropic_attribute(
            df_one_fp_per_browser, current_attributes, candidate_attributes)
        logger.debug(f'  The best attribute is {best_attribute} for a total '
                     f'entropy of {best_total_ent}.')
        return best_attribute

    # The values to update through the search for the best attribute
    best_attribute_information = {}
    logger.debug('Measuring the attributes conditional entropy using '
                 'multiprocessing...')

    # Infer the number of cores to use
    free_cores = params.getint('Multiprocessing', 'free_cores')
    nb_cores = max(cpu_count() - free_cores, 1)
    attributes_per_core = int(ceil(len(candidate_attributes)/nb_cores))
    logger.debug(f'Sharing {len(candidate_attributes)} candidate attributes '
                 f'over {nb_cores}(+{free_cores}) cores, hence '
                 f'{attributes_per_core} attributes per core.')

    def update_best_conditional_entropy_attribute(result: Tuple[Attribute,
                                                                float]):
        """Update the best conditional entropy attribute.

        Args:
            result: A tuple with the best attribute and the best total entropy.

        Note: This is executed by the main thread and does not pose any
              concurrency or synchronization problem.
        """
        _best_attribute, _best_total_entropy = result
        if _best_attribute:  # To avoid the empty results which are None
            best_attribute_information[_best_attribute] = _best_total_entropy

    # Spawn a number of processes equal to the number of cores
    candidate_attributes_list = list(candidate_attributes)
    async_results = []
    with Pool(processes=nb_cores) as pool:
        for process_id in range(nb_cores):
            # Generate the candidate attributes for this process
            start_id = process_id * attributes_per_core
            end_id = (process_id + 1) * attributes_per_core
            candidate_attributes_subset = AttributeSet(
                candidate_attributes_list[start_id:end_id])

            async_result = pool.apply_async(
                best_conditional_entropic_attribute,
                args=(df_one_fp_per_browser, current_attributes,
                      candidate_attributes_subset),
                callback=update_best_conditional_entropy_attribute)
            async_results.append(async_result)

        # Wait for all the processes to finish (otherwise we would exit
        # before collecting their result)
        for async_result in async_results:
            async_result.wait()

    # Search for the best attribute in the local results. If several provide
    # the same total entropy, we provide the attribute having the lowest id.
    best_attribute, best_total_entropy = None, -float('inf')
    for attribute in sorted(best_attribute_information):
        attribute_total_entropy = best_attribute_information[attribute]
        if attribute_total_entropy > best_total_entropy:
            best_total_entropy = attribute_total_entropy
            best_attribute = attribute

    logger.debug(f'  The best attribute is {best_attribute} for a total '
                 f'entropy of {best_total_entropy}.')

    return best_attribute


def best_conditional_entropic_attribute(df_one_fp_per_browser: pd.DataFrame,
                                        current_attributes: AttributeSet,
                                        candidate_attributes: AttributeSet
                                        ) -> Tuple[Attribute, float]:
    """Get the best conditional entropic attribute among the candidates.

    Args:
        df_one_fp_per_browser: The dataframe with only one fingerprint per
                               browser.
        current_attributes: The attributes that compose the current solution.
        candidate_attributes: The candidate attributes for this process to
                              check.

    Returns:
        A tuple with the best attribute for this process and the total entropy
        when adding this attribute to the current attributes.
    """
    best_local_attribute, best_local_total_entropy = None, -float('inf')
    for attribute in candidate_attributes:

        # Ignore the attributes that are already in the current attribute set
        if attribute in current_attributes:
            continue

        # Generate a new attribute set with this attribute
        attribute_set = AttributeSet(current_attributes)
        attribute_set.add(attribute)

        # Evaluate the conditional entropy of this new attribute set and save
        # it in the dictionary
        attr_set_entropy = attribute_set_entropy(df_one_fp_per_browser,
                                                 attribute_set)
        if attr_set_entropy > best_local_total_entropy:
            best_local_attribute = attribute
            best_local_total_entropy = attr_set_entropy

    return best_local_attribute, best_local_total_entropy


class ConditionalEntropy(Exploration):
    """The exploration algorithm based on conditional entropy."""

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
        # The temporary solution (empty set) and the current sensitivity (1.0
        # as it is equivalent to no browser fingerprinting used at all)
        temp_solution, sensitivity = AttributeSet(), 1.0

        # We already checked that the sensitivity threshold is reachable, hence
        # we always reach it when processing the Exploration
        while sensitivity > self._sensitivity_threshold:

            # Find the attribute that has the highest conditional entropy
            best_cond_ent_attr = get_best_conditional_entropic_attribute(
                self._dataset, temp_solution,
                self._dataset.candidate_attributes)

            # NOTE Removed as we already check that a solution exists before
            #      running the exploration. As a result, we always reach an
            #      attribute set that satisfies the sensitivity threshold, the
            #      complete set of the candidate attributes in the worst case.
            # If no more solution is proposed, end the exploration
            # if not best_cond_ent_attr:
            #     break

            # Add this attribute to the temporary solution
            temp_solution.add(best_cond_ent_attr)

            # Compute its sensitivity and its cost
            logger.debug(f'Exploring {temp_solution}...')
            sensitivity = self._sensitivity.evaluate(temp_solution)
            cost, cost_explanation = (
                self._usability_cost.evaluate(temp_solution))
            logger.debug(f'  Sensitivity ({sensitivity}), '
                         f'usability cost ({cost})')

            # If it satisfies the sensitivity threshold, quit the loop
            if sensitivity <= self._sensitivity_threshold:
                self._update_solution(temp_solution)
                attribute_set_state = State.SATISFYING
                self._add_satisfying_attribute_set(temp_solution)
            else:
                attribute_set_state = State.EXPLORED

            # Store this attribute set in the explored sets
            compute_time = str(datetime.now() - self._start_time)
            self._add_explored_attribute_set({
                TraceData.TIME: compute_time,
                TraceData.ATTRIBUTES: temp_solution.attribute_ids,
                TraceData.SENSITIVITY: sensitivity,
                TraceData.USABILITY_COST: cost,
                TraceData.COST_EXPLANATION: cost_explanation,
                TraceData.STATE: attribute_set_state
            })
