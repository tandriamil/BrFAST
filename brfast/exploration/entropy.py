#!/usr/bin/python3
"""Module containing the entropy-based exploration algorithm."""

from datetime import datetime

from loguru import logger

from brfast.exploration import Exploration, State, TraceData
from brfast.data import AttributeSet, FingerprintDataset
from brfast.measures.distinguishability.entropy import attribute_set_entropy
from brfast.utils.sequences import sort_dict_by_value


def _get_attributes_entropy(dataset: FingerprintDataset,
                            attributes: AttributeSet):
    """Give a dictionary with the entropy of each attribute.

    Args:
        dataset: The fingerprint dataset used to compute the entropy.
        attributes: The attributes for which we compute the entropy.

    Returns:
        A dictionary with each attribute (Attribute) and its entropy.
    """
    attributes_entropy = {}
    for attribute in attributes:
        attributes_entropy[attribute] = attribute_set_entropy(
            dataset, AttributeSet([attribute]))
        logger.debug(f'  entropy({attribute.name}) = '
                     f'{attributes_entropy[attribute]}')
    return attributes_entropy


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
        attributes_entropy = _get_attributes_entropy(
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
                self._solution = attribute_set
                self._satisfying_attribute_sets.add(attribute_set)

                # Store this attribute set in the explored sets
                compute_time = str(datetime.now() - self._start_time)
                self._explored_attr_sets.append({
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
            self._explored_attr_sets.append({
                TraceData.TIME: compute_time,
                TraceData.ATTRIBUTES: attribute_set.attribute_ids,
                TraceData.SENSITIVITY: sensitivity,
                TraceData.USABILITY_COST: cost,
                TraceData.COST_EXPLANATION: cost_explanation,
                TraceData.STATE: State.EXPLORED
            })
