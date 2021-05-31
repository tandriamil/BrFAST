#!/usr/bin/python3
"""Module containing the interfaces of the exploration classes."""

import json
from datetime import datetime, timedelta
from enum import IntEnum
from multiprocessing import Manager, Process
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from sortedcontainers import SortedDict, SortedList

from brfast.config import ANALYSIS_ENGINES, params
from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.measures import SensitivityMeasure, UsabilityCostMeasure


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

        # Create a manager to have a shared memory between the processes
        self._manager = Manager()

        # The attributes that are shared between the processes and that should
        # be updated during the exploration
        self._solution = self._manager.list([None])
        self._satisfying_attribute_sets = self._manager.list()
        self._explored_attr_sets = self._manager.list()

        # The start time and the max cost will be set during the exploration
        self._start_time, self._execution_time = None, None
        self._max_cost = float('inf')

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
        logger.info('Start running the exploration in sequential manner...')

        # Hold the start time to measure the time taken by each measure
        self._start_time = datetime.now()
        logger.debug(f'Starting the exploration at {self._start_time}.')

        # Then, check that the sensitivity threshold is reachable
        if not self._is_sensitivity_threshold_reachable():
            warning_message = (
                f'The sensivity threshold of {self._sensitivity_threshold} '
                'is not reachable even using all the '
                f'{len(self._dataset.candidate_attributes)} candidate '
                'attributes.')
            logger.warning(warning_message)
            raise SensitivityThresholdUnreachable(warning_message)

        # If a solution exists, search for a solution
        logger.info('The sensitivity threshold is reachable, searching for a '
                    'solution now...')
        self._search_for_solution()

        # A little message when the exploration is done
        self._execution_time = datetime.now() - self._start_time
        logger.info(f'The exploration is done after {self._execution_time}.')
        logger.info(f'{len(self._explored_attr_sets)} attribute sets were '
                    'explored, among which '
                    f'{len(self._satisfying_attribute_sets)} satisfy the '
                    'sensitivity threshold.')

    def run_asynchronous(self) -> Process:
        """Run the search for a solution in an asynchronous manner.

        Returns:
            The process that runs the search for a solution.
        """
        logger.info('Start running the exploration in asynchronous manner...')

        # Hold the start time to measure the time taken by each measure
        self._start_time = datetime.now()
        logger.debug(f'Starting the exploration at {self._start_time}.')

        # Create, start, and return a process that runs the exploration
        process = Process(target=self._asynchronous_execution)
        process.start()
        return process

    def _asynchronous_execution(self):
        """Run the exploration in another process."""
        # Then, check that the sensitivity threshold is reachable
        if not self._is_sensitivity_threshold_reachable():
            logger.warning(
                f'The sensivity threshold of {self._sensitivity_threshold} '
                'is not reachable even using all the '
                f'{len(self._dataset.candidate_attributes)} candidate '
                'attributes.')
            return

        # If a solution exists, search for a solution
        logger.info('The sensitivity threshold is reachable, searching for'
                    ' a solution now...')
        self._search_for_solution()

        # A little message when the exploration is done
        self._execution_time = datetime.now() - self._start_time
        logger.info(f'The exploration is done after {self._execution_time}.')
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
            Whether the sensitivity threshold is reachable.
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
            self._add_satisfying_attribute_set(
                self._dataset.candidate_attributes)
        else:
            candidate_attributes_state = State.EXPLORED

        # Store this attribute set in the explored sets
        compute_time = str(datetime.now() - self._start_time)
        self._add_explored_attribute_set({
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

    def _default_parameters(self) -> Dict[str, Any]:
        """Give the parameters that are always present in an exploration.

        Returns:
            A dictionary with the default parameters of an exploration.
        """
        analysis_engine = params.get('DataAnalysis', 'engine')
        if analysis_engine == ANALYSIS_ENGINES[1]:
            modin_engine = params.get('DataAnalysis', 'modin_engine')
            analysis_engine += f"[{modin_engine}]"
        return {
            ExplorationParameters.METHOD: self.__class__.__name__,
            ExplorationParameters.SENSITIVITY_MEASURE: str(self._sensitivity),
            ExplorationParameters.USABILITY_COST_MEASURE: str(
                self._usability_cost),
            ExplorationParameters.DATASET: str(self._dataset),
            ExplorationParameters.SENSITIVITY_THRESHOLD: (
                self._sensitivity_threshold),
            ExplorationParameters.ANALYSIS_ENGINE: analysis_engine,
            ExplorationParameters.MULTIPROCESSING: params.getboolean(
                'Multiprocessing', 'explorations'),
            ExplorationParameters.FREE_CORES: params.getint('Multiprocessing',
                                                            'free_cores')
        }

    @property
    def parameters(self) -> Dict[str, Any]:
        """Give the parameters of the exploration as a dictionary.

        Returns:
            The parameters as a dictionary of their name and their value.
        """
        return self._default_parameters()

    def _check_exploration_state(self):
        """Check the exploration state before providing results.

        Raises:
            ExplorationNotRun: The exploration was not run.
            SensitivityThresholdUnreachable: In asynchronous run: the
                                             sensitivity threshold is
                                             unreachable.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')

        # If the run was launched, some attribute sets were explored but no
        # attribute sets satisfy the sensitivity threshold, this means that the
        # complete set of attributes does not satisfy the sensitivity threshold
        if not self._satisfying_attribute_sets and self._explored_attr_sets:
            raise SensitivityThresholdUnreachable(
                'The sensitivity is unreachable (asynchronous run).')

    def get_solution(self) -> AttributeSet:
        """Provide the solution found by the algorithm after the exploration.

        Returns:
            The AttributeSet that satisfies the sensitivity threshold at the
            lowest cost according to the exploration method (no optimality
            guaranteed).

        Raises:
            ExplorationNotRun: The exploration was not run.
            SensitivityThresholdUnreachable: In asynchronous run: the
                                             sensitivity threshold is
                                             unreachable.
        """
        self._check_exploration_state()
        # Create a new AttributeSet to exit the shared memory space
        return AttributeSet(self._solution[0])

    def _update_solution(self, new_solution: AttributeSet):
        """Update the best solution currently found.

        This solution is the attribute set that satisfies the sensitivity
        threshold at the lowest cost.

        Args:
            new_solution: The new solution found.
        """
        self._solution[0] = new_solution

    def get_satisfying_attribute_sets(self) -> Set[AttributeSet]:
        """Provide the attribute sets that satisfy the sensitivity threshold.

        Returns:
            The AttributeSet that satisfies the sensitivity threshold at the
            lowest cost according to the exploration method (no optimality
            guaranteed).

        Raises:
            ExplorationNotRun: The exploration was not run.
            SensitivityThresholdUnreachable: In asynchronous run: the
                                             sensitivity threshold is
                                             unreachable.
        """
        self._check_exploration_state()
        # Generate a set and exit the shared memory space
        return set(self._satisfying_attribute_sets)

    def _add_satisfying_attribute_set(self, new_attribute_set: AttributeSet):
        """Add a new attribute set that satisfies the sensitivity threshold.

        Args:
            new_attribute_set: The new attribute set that satisfies the
                               sensitivity threshold.
        """
        self._satisfying_attribute_sets.append(new_attribute_set)

    def get_explored_attribute_sets(self, start_id: Optional[int] = None,
                                    end_id: Optional[int] = None
                                    ) -> List[AttributeSet]:
        """Provide the attribute sets that were explored.

        Args:
            start_id: The starting id of the sublist to consider.
            end_id: The ending id of the sublist to consider.

        Returns:
            The AttributeSet that were explored in the order of exploration.

        Raises:
            ExplorationNotRun: The exploration was not run.
        """
        if not self._start_time:
            raise ExplorationNotRun('The exploration was not run.')

        # Create a new list to exit the shared memory space
        if start_id is None:
            start_id = 0
        if end_id is None:
            return list(self._explored_attr_sets[start_id:])
        return list(self._explored_attr_sets[start_id:end_id])

    def _add_explored_attribute_set(self, new_attribute_set: AttributeSet):
        """Add a new attribute set that was explored.

        Args:
            new_attribute_set: The new attribute set that satisfies the
                               sensitivity threshold.
        """
        self._explored_attr_sets.append(new_attribute_set)

    def get_execution_time(self) -> Optional[timedelta]:
        """Provide the execution time of the exploration.

        Returns:
            The execution time of the exploration as a timedelta. None if the
            exploration is still ongoing.

        Raises:
            ExplorationNotRun: The exploration was not run.
            SensitivityThresholdUnreachable: In asynchronous run: the
                                             sensitivity threshold is
                                             unreachable.
        """
        self._check_exploration_state()
        return self._execution_time

    def save_exploration_trace(self, save_path: str):
        """Save the trace registered during the exploration as a json file.

        Args:
            save_path: Path to the file where to save the trace in json format.

        Raises:
            ExplorationNotRun: The exploration was not run.
            SensitivityThresholdUnreachable: In asynchronous run: the
                                             sensitivity threshold is
                                             unreachable.
        """
        self._check_exploration_state()
        logger.info(f'Saving the exploration trace to {save_path}...')

        # The json dictionary to save (as a python dict)
        json_output = {}

        # Information about the parameters of the exploration
        json_output[TraceData.PARAMETERS] = self.parameters

        # Information about the attributes
        json_output[TraceData.ATTRIBUTES] = SortedDict()
        for attribute in self._dataset.candidate_attributes:
            json_output[TraceData.ATTRIBUTES][attribute.attribute_id] = (
                attribute.name)

        # The ids of the satisfying attributes
        satisfying_attributes_id = [
            [attribute.attribute_id for attribute in satisfying_attr_set]
            for satisfying_attr_set in self.get_satisfying_attribute_sets()]

        # Information about the results
        result = {
            TraceData.SOLUTION: [attribute.attribute_id
                                 for attribute in self.get_solution()],
            TraceData.SATISFYING_ATTRIBUTES: satisfying_attributes_id,
            TraceData.START_TIME: str(self._start_time)
        }
        json_output[TraceData.RESULT] = result

        # Information about the actual exploration
        json_output[TraceData.EXPLORATION] = []
        explored_attribute_sets = self.get_explored_attribute_sets()
        for i, explr_set_information in enumerate(explored_attribute_sets):
            explr_set_information[TraceData.ATTRIBUTE_SET_ID] = i
            json_output[TraceData.EXPLORATION].append(explr_set_information)

        # Save the exploration data as a json file
        with open(save_path, 'w+') as save_file:
            json.dump(json_output, save_file)

        logger.info(f'The exploration is saved at {save_path}.')


# ============================== Utility Classes ==============================
class State(IntEnum):
    """The states of an explored attribute set."""

    EXPLORED = 1
    PRUNED = 2
    SATISFYING = 3
    EMPTY_NODE = 4


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
    ANALYSIS_ENGINE = 'analysis_engine'
    MULTIPROCESSING = 'multiprocessing'
    FREE_CORES = 'free_cores'


class ExplorationNotRun(Exception):
    """Exception raised when accessing an attribute before the exploration."""


class SensitivityThresholdUnreachable(Exception):
    """Exception raised when the sensitivity threshold is unreachable."""
# =========================== End of Utility Classes ==========================
