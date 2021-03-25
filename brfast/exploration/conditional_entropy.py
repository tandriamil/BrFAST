#!/usr/bin/python3
"""Module containing the exploration algorithm based on conditional entropy."""

from datetime import datetime

from loguru import logger

from brfast.exploration import Exploration, State, TraceData
from brfast.data import Attribute, AttributeSet, FingerprintDataset
from brfast.measures.distinguishability.entropy import attribute_set_entropy


def _get_best_conditional_entropic_attribute(dataset: FingerprintDataset,
                                             current_attributes: AttributeSet,
                                             candidate_attributes: AttributeSet
                                             ) -> Attribute:
    """Get the best conditional entropy attribute.

    Args:
        dataset: The dataset used to compute the conditional entropy.
        current_attributes: The attributes that compose the current solution.
        candidate_attributes: The candidate attributes (i.e., those available).

    Returns:
        The attribute that has the highest conditional entropy among the
        candidate attributes and that is not part of the current attributes.
    """
    logger.debug('Getting the best conditional entropic attribute from '
                 f'{current_attributes}...')

    # best_conditional_entropy is initialized to 0.0 to stop proposing a new
    # attribute when no more attribute provides additional distinguishing
    # information.
    best_attribute, best_conditional_entropy = None, 0.0
    for attribute in candidate_attributes:

        # Ignore the attributes that are already in the current attribute set
        if attribute in current_attributes:
            continue

        # Generate a new attribute set with this attribute
        attribute_set = AttributeSet(current_attributes)
        attribute_set.add(attribute)

        # Evaluate the conditional entropy of this new attribute set
        attr_set_entropy = attribute_set_entropy(dataset, attribute_set)
        if attr_set_entropy > best_conditional_entropy:
            best_attribute = attribute
            best_conditional_entropy = attr_set_entropy

    logger.debug(f'  The best attribute is {best_attribute} for a total '
                 f'entropy of {best_conditional_entropy}.')
    return best_attribute


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
        temp_solution, sensitivity = AttributeSet(), 1.0
        while sensitivity > self._sensitivity_threshold:

            # Find the attribute that has the highest conditional entropy
            best_cond_ent_attr = _get_best_conditional_entropic_attribute(
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
                self._solution = temp_solution
                attribute_set_state = State.SATISFYING
                self._satisfying_attribute_sets.add(temp_solution)
            else:
                attribute_set_state = State.EXPLORED

            # Store this attribute set in the explored sets
            compute_time = str(datetime.now() - self._start_time)
            self._explored_attr_sets.append({
                TraceData.TIME: compute_time,
                TraceData.ATTRIBUTES: temp_solution.attribute_ids,
                TraceData.SENSITIVITY: sensitivity,
                TraceData.USABILITY_COST: cost,
                TraceData.COST_EXPLANATION: cost_explanation,
                TraceData.STATE: attribute_set_state
            })
