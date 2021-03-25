#!/usr/bin/python3
"""Module containing the interfaces of the exploration classes."""

import json
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Set

from loguru import logger
from sortedcontainers import SortedDict, SortedList

from brfast.measures import SensitivityMeasure, UsabilityCostMeasure
from brfast.data import AttributeSet, FingerprintDataset


class State(IntEnum):
    """The states of an explored attribute set."""

    EXPLORED = 1
    PRUNED = 2
    SATISFYING = 3


class TraceData:
    """Class representing the data stored in the trace."""

    # About the exploration
    EXPLORATION = 'exploration'
    PARAMETERS = 'parameters'
    RESULT = 'result'
    SATISFYING_ATTRIBUTES = 'satisfying_attributes'
    SOLUTION = 'solution'
    START_TIME = 'start_time'

    # About an explored attribute set
    ATTRIBUTE_SET_ID = 'id'
    ATTRIBUTES = 'attributes'
    COST_EXPLANATION = 'cost_explanation'
    SENSITIVITY = 'sensitivity'
    STATE = 'state'
    TIME = 'time'
    USABILITY_COST = 'usability_cost'


class ExplorationParameters:
    """Class representing the default parameters of an exploration."""

    DATASET = 'dataset'
    METHOD = 'method'
    SENSITIVITY_MEASURE = 'sensitivity_measure'
    SENSITIVITY_THRESHOLD = 'sensitivity_threshold'
    USABILITY_COST_MEASURE = 'usability_cost_measure'


class ExplorationNotRun(Exception):
    """Exception raised when accessing an attribute before the exploration."""


class SensitivityThresholdUnreachable(Exception):
    """Exception raised when the sensitivity threshold is unreachable."""


class Exploration:
    """The class of an exploration set with the different parameters."""

    def __init__(self, sensitivity_measure: SensitivityMeasure,
                 usability_cost_measure: UsabilityCostMeasure,
                 dataset: FingerprintDataset, sensitivity_threshold: float):
        """Initialize an exploration.

        Args:
            sensitivity_measure: The sensitivity measure.
            usability_cost_measure: The usability cost.
            dataset: The fingerprint dataset.
            sensitivity_threshold: The sensivity threshold.
        """
        self._sensitivity = sensitivity_measure
        self._usability_cost = usability_cost_measure
        self._dataset = dataset
        self._sensitivity_threshold = sensitivity_threshold
        # The attributes to update during the exploration
        self._solution, self._satisfying_attribute_sets = None, set()
        self._explored_attr_sets = []
        self._max_cost = float('inf')
        # The start time will be set when running the exploration
        self._start_time = None

        # Some info/debug messages
        candidate_attributes = self._dataset.candidate_attributes
        logger.info('Initialized the exploration algorithm '
                    f'{self.__class__.__name__}.')
        logger.info(f'Considering {len(candidate_attributes)} candidate '
                    'attributes.')
        logger.debug(f'The candidate attributes: {candidate_attributes}.')
        logger.info('Setting the sensitivity threshold to '
                    f'{self._sensitivity_threshold}.')
        logger.info('Setting the usability cost measure to '
                    f'{self._usability_cost}.')
        logger.info(f'Setting the sensitivity measure to {self._sensitivity}.')

    def __repr__(self) -> str:
        """Provide a string representation of this instance of FPSelect.

        Returns:
            A string representation of this instance of FPSelect.
        """
        str_informations = ', '. join(
            f'{key} = {value}' for key, value in self.parameters.items())
        return f'{self.__class__.__name__}({str_informations})'

    def run(self):
        """Run the search for a solution for the attribute search problem.

        Raises:
            SensitivityThresholdUnreachable: The sensitivity threshold is
                                             unreachable.
        """
        logger.info('Start running the exploration...')

        # Hold the start time to measure the time taken by each measure
        self._start_time = datetime.now()

        # Then, check that the sensitivity threshold is reachable
        if not self._is_sensitivity_threshold_reachable():
            raise SensitivityThresholdUnreachable(
                'The sensitivity threshold is not reachable even using all the'
                f' {len(self._dataset.candidate_attributes)} candidate '
                'attributes.')

        # If a solution exists, search for a solution
        logger.info('The sensitivity threshold is reachable, searching for a '
                    'solution now...')
        self._search_for_solution()

        # A little message when the exploration is done
        diff_w_start_time = datetime.now() - self._start_time
        logger.info(f'The exploration is done after {diff_w_start_time}.')
        logger.info(f'{len(self._explored_attr_sets)} attribute sets were '
                    'explored, among which '
                    f'{len(self._satisfying_attribute_sets)} satisfy the '
                    'sensitivity threshold.')

    def _search_for_solution(self):
        """Search for a solution using the exploration algorithm.

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

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        raise NotImplementedError

    def _is_sensitivity_threshold_reachable(self) -> bool:
        """Check that the sensitivity is reachable using all the attributes.

        It computes the minimum sensitivity obtained when considering all the
        attributes, and checks whether this minimum is below the sensitivity
        threshold. If it is not, no solution exists as all the attribute
        subsets will show a higher sensitivity.

        Returns:
            If the sensitivity threshold is reachable.
        """
        logger.info('Checking if the sensitivity threshold of '
                    f'{self._sensitivity_threshold} is reachable when using '
                    f'the {len(self._dataset.candidate_attributes)} candidate '
                    'attributes.')

        # The maximum cost when considering the complete set of attributes
        self._max_cost, max_cost_explanation = self._usability_cost.evaluate(
            self._dataset.candidate_attributes)
        logger.debug(f'The maximum cost is {self._max_cost} which is '
                     f'explained as {max_cost_explanation}.')

        # Compute the sensitivity considering the complete set of attributes
        sensitivity_canditate_attributes = self._sensitivity.evaluate(
            self._dataset.candidate_attributes)
        logger.debug('The minimum sensivity threshold is of '
                     f'{sensitivity_canditate_attributes}.')

        # Check if the minimum sensitivity satifies the threshold
        min_sensitivity_satisfies_threshold = (
            sensitivity_canditate_attributes <= self._sensitivity_threshold)
        if min_sensitivity_satisfies_threshold:
            candidate_attributes_state = State.SATISFYING
            self._satisfying_attribute_sets.add(
                self._dataset.candidate_attributes)
        else:
            candidate_attributes_state = State.EXPLORED

        # Store this attribute set in the explored sets
        compute_time = str(datetime.now() - self._start_time)
        self._explored_attr_sets.append({
            TraceData.TIME: compute_time,
            TraceData.ATTRIBUTES: (
                self._dataset.candidate_attributes.attribute_ids),
            TraceData.SENSITIVITY: sensitivity_canditate_attributes,
            TraceData.USABILITY_COST: self._max_cost,
            TraceData.COST_EXPLANATION: max_cost_explanation,
            TraceData.STATE: candidate_attributes_state
        })

        # Return whether the minimum sensitivity satisfies the threshold
        return min_sensitivity_satisfies_threshold

    @property
    def parameters(self) -> Dict[str, Any]:
        """Give the parameters of the exploration as a dictionary.

        Returns:
            The parameters as a dictionary of their name and their value.
        """
        return {
            ExplorationParameters.METHOD: self.__class__.__name__,
            ExplorationParameters.SENSITIVITY_MEASURE: str(self._sensitivity),
            ExplorationParameters.USABILITY_COST_MEASURE: str(
                self._usability_cost),
            ExplorationParameters.DATASET: str(self._dataset),
            ExplorationParameters.SENSITIVITY_THRESHOLD: (
                self._sensitivity_threshold)
        }

    def get_solution(self) -> AttributeSet:
        """Provide the solution found by the algorithm after the exploration.

        Returns:
            The AttributeSet that satisfies the sensitivity threshold at the
            lowest cost according to the exploration method (no optimality
            guaranteed).

        Raises:
            ExplorationNotRun: The exploration was not run.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')
        return self._solution

    def get_satisfying_attribute_sets(self) -> Set[AttributeSet]:
        """Provide the attribute sets that satisfy the sensitivity threshold.

        Returns:
            The AttributeSet that satisfies the sensitivity threshold at the
            lowest cost according to the exploration method (no optimality
            guaranteed).

        Raises:
            ExplorationNotRun: The exploration was not run.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')
        return self._satisfying_attribute_sets

    def get_explored_attribute_sets(self) -> List[AttributeSet]:
        """Provide the attribute sets that were explored.

        Returns:
            The AttributeSet that were explored in the order of exploration.

        Raises:
            ExplorationNotRun: The exploration was not run.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')
        return self._explored_attr_sets

    def save_exploration_trace(self, save_path: str):
        """Save the trace registered during the exploration as a json file.

        Args:
            save_path: Path to the file where to save the trace in json format.

        Raises:
            ExplorationNotRun: The exploration was not run.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')
        logger.info(f'Saving the exploration trace to {save_path}...')

        # The json dictionary to save (as a python dict)
        json_output = {}

        # Information about the parameters of the exploration
        json_output[TraceData.PARAMETERS] = self.parameters

        # Information about the attributes
        json_output[TraceData.ATTRIBUTES] = SortedDict()
        for attribute in self._dataset.candidate_attributes:
            json_output[TraceData.ATTRIBUTES][attribute.attr_id] = (
                attribute.name)

        # Information about the results
        result = {
            TraceData.SOLUTION: [attribute.attr_id
                                 for attribute in self._solution],
            TraceData.SATISFYING_ATTRIBUTES: [
                [attribute.attr_id for attribute in satisfying_attr_set]
                for satisfying_attr_set in self._satisfying_attribute_sets],
            TraceData.START_TIME: str(self._start_time)
        }
        json_output[TraceData.RESULT] = result

        # Information about the actual exploration
        json_output[TraceData.EXPLORATION] = []
        for i, explr_set_information in enumerate(self._explored_attr_sets):
            explr_set_information[TraceData.ATTRIBUTE_SET_ID] = i
            json_output[TraceData.EXPLORATION].append(explr_set_information)

        # Save the exploration data as a json file
        with open(save_path, 'w+') as save_file:
            json.dump(json_output, save_file)

        logger.info(f'The exploration is saved at {save_path}.')
