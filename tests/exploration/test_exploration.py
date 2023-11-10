#!/usr/bin/python3
"""Test module of the exploration module of BrFAST."""

import json
import unittest
from os import path, remove
from pathlib import PurePath
from typing import List, Optional, Set

from brfast.config import ANALYSIS_ENGINES, params
from brfast.data.attribute import AttributeSet
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, TraceData)
from tests.data import ATTRIBUTES, DummyCleanDataset
from tests.exploration import (
    DUMMY_PARAMETER, DummyExploration, SENSITIVITY_THRESHOLD, TRACE_FILENAME,
    MODIN_ANALYSIS_ENGINES)
from tests.measures import (DummySensitivity, DummyUsabilityCostMeasure)
from tests.utils import remove_key_if_present

EXPECTED_TRACE_PATH = 'assets/traces/expected_trace_dummy_exploration.json'


class TestExploration(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = DummyExploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        params.set('Multiprocessing', 'explorations', 'false')

    def test_repr(self):
        self.assertIsInstance(str(self._exploration), str)

    def test_exploration_base_class(self):
        self._exploration = Exploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        self.check_parameters()
        with self.assertRaises(NotImplementedError):
            # _search_for_solution is abstract and not defined for Exploration
            self._exploration.run()

    def check_parameters(self, additional_parameters: Optional[dict] = None):
        exploration_parameters = dict(self._exploration.parameters)

        expected_parameters = {
            ExplorationParameters.METHOD: self._exploration.__class__.__name__,
            ExplorationParameters.SENSITIVITY_MEASURE: str(
                self._sensitivity_measure),
            ExplorationParameters.USABILITY_COST_MEASURE: str(
                self._usability_cost_measure),
            ExplorationParameters.DATASET: str(self._dataset),
            ExplorationParameters.SENSITIVITY_THRESHOLD: (
                self._sensitivity_threshold)
        }

        # ===== Remove the parameters that we do not really care
        # The analysis engine
        self.assertTrue(
            ExplorationParameters.ANALYSIS_ENGINE in exploration_parameters)
        analysis_engine = exploration_parameters[
            ExplorationParameters.ANALYSIS_ENGINE]
        self.assertIn(analysis_engine, ANALYSIS_ENGINES)
        remove_key_if_present(exploration_parameters,
                              ExplorationParameters.ANALYSIS_ENGINE)

        # The usage of multiprocessing
        self.assertTrue(
            ExplorationParameters.MULTIPROCESSING in exploration_parameters)
        use_multiprocessing = exploration_parameters[
            ExplorationParameters.MULTIPROCESSING]
        self.assertIsInstance(use_multiprocessing, bool)
        remove_key_if_present(exploration_parameters,
                              ExplorationParameters.MULTIPROCESSING)

        # The number of free cores left to the system
        self.assertTrue(
            ExplorationParameters.FREE_CORES in exploration_parameters)
        free_cores = exploration_parameters[ExplorationParameters.FREE_CORES]
        self.assertIsInstance(free_cores, int)
        self.assertTrue(free_cores >= 0)
        remove_key_if_present(exploration_parameters,
                              ExplorationParameters.FREE_CORES)
        # ===== End of removing the parameters that we do not really care

        # Add the additional parameters if there are some
        if additional_parameters:
            for additional_parameter, value in additional_parameters.items():
                expected_parameters[additional_parameter] = value

        # Compare the two obtained dictionaries
        self.assertDictEqual(exploration_parameters, expected_parameters)

        # Check that the parameters property is not writable
        with self.assertRaises(AttributeError):
            self._exploration.parameters = {'refused_as_it_is': 'readonly'}  # noqa

    def test_parameters(self):
        additional_parameters = DUMMY_PARAMETER
        self.check_parameters(additional_parameters)

    def test_exploration_not_ran(self):
        with self.assertRaises(ExplorationNotRun):
            self._exploration.get_solution()
        with self.assertRaises(ExplorationNotRun):
            self._exploration.get_satisfying_attribute_sets()
        with self.assertRaises(ExplorationNotRun):
            self._exploration.get_explored_attribute_sets()
        with self.assertRaises(ExplorationNotRun):
            self._exploration.get_execution_time()
        with self.assertRaises(ExplorationNotRun):
            self._exploration.save_exploration_trace(self._trace_path)

    def test_run_sensitivity_unreachable(self):
        unreachable_sensitivity_threshold = 0.0
        unreachable_exploration = self._exploration.__class__(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold)
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.run()

    def test_run_asynchronous_sensitivity_unreachable(self):
        unreachable_sensitivity_threshold = 0.0
        unreachable_exploration = self._exploration.__class__(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold)
        process = unreachable_exploration.run_asynchronous()
        process.join()  # Wait for the process to end
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.get_solution()
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.get_satisfying_attribute_sets()
        # with self.assertRaises(SensitivityThresholdUnreachable):
        #     unreachable_exploration.get_explored_attribute_sets()
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.get_execution_time()

    def check_run(self, expected_solution: AttributeSet,
                  expected_satisfying_attribute_sets: Set[AttributeSet],
                  expected_explored_attribute_sets: List[dict],
                  check_exploration=True):
        # Check that the solution is the one expected
        self.assertEqual(self._exploration.get_solution(), expected_solution)

        # Check that the satisfying attributes are the right ones
        self.assertEqual(self._exploration.get_satisfying_attribute_sets(),
                         expected_satisfying_attribute_sets)

        # Remove the dynamic start_time of the exploration traces
        explored_attribute_sets = (
            self._exploration.get_explored_attribute_sets())
        for explored_attribute in explored_attribute_sets:
            remove_key_if_present(explored_attribute, TraceData.TIME)
        for expected_explored_attribute in expected_explored_attribute_sets:
            remove_key_if_present(expected_explored_attribute, TraceData.TIME)
            remove_key_if_present(expected_explored_attribute,
                                  TraceData.ATTRIBUTE_SET_ID)

        # Check that the explored attribute sets are the right ones
        if check_exploration:
            self.assertEqual(explored_attribute_sets,
                             expected_explored_attribute_sets)

    def test_run(self):
        # Run the exploration
        self._exploration.run()
        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        expected_satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1], ATTRIBUTES[2]})}
        expected_explored_attribute_sets = (
            DummyExploration.EXPLORED_ATTRIBUTE_SETS)
        self.check_run(expected_solution, expected_satisfying_attribute_sets,
                       expected_explored_attribute_sets)

    def test_run_asynchronous(self):
        # Run the exploration
        process = self._exploration.run_asynchronous()
        process.join()  # Wait for the process to end
        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        expected_satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1], ATTRIBUTES[2]})}
        expected_explored_attribute_sets = (
            DummyExploration.EXPLORED_ATTRIBUTE_SETS)
        self.check_run(expected_solution, expected_satisfying_attribute_sets,
                       expected_explored_attribute_sets)

    def _check_save_trace(self, check_exploration=True):
        # Save the exploration trace
        self._exploration.save_exploration_trace(self._trace_path)

        # Load the comparison file as a json dictionary
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        comparison_trace_path = tests_module_path.joinpath(
            self._expected_trace_path)
        with open(comparison_trace_path, 'r') as comparison_file:
            comparison_dict = json.load(comparison_file)

        # Load the saved trace file as a json dictionary
        with open(self._trace_path, 'r') as saved_trace_file:
            saved_trace_dict = json.load(saved_trace_file)

        # Remove the dynamic start_time of each of these files
        remove_key_if_present(comparison_dict, [TraceData.RESULT,
                                                TraceData.START_TIME])
        remove_key_if_present(saved_trace_dict, [TraceData.RESULT,
                                                 TraceData.START_TIME])

        # Check and then remove the dataset information which contains its path
        # that includes the path of the dataset (which is its file in fact)
        comparison_dataset_info = comparison_dict[TraceData.PARAMETERS][
            ExplorationParameters.DATASET]
        # NOTE The comparison dict that is read is given as a file and contains
        #      the path of my own laptop. No need to verify it.
        # self.assertEqual(comparison_dataset_info, str(self._dataset))
        remove_key_if_present(comparison_dict, [TraceData.PARAMETERS,
                                                ExplorationParameters.DATASET])
        saved_trace_dataset_info = saved_trace_dict[TraceData.PARAMETERS][
                ExplorationParameters.DATASET]
        self.assertEqual(saved_trace_dataset_info, str(self._dataset))
        remove_key_if_present(saved_trace_dict, [
            TraceData.PARAMETERS, ExplorationParameters.DATASET])

        # Check the analysis engine
        saved_analysis_engine = saved_trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.ANALYSIS_ENGINE]
        expected_analysis_engines = ANALYSIS_ENGINES + MODIN_ANALYSIS_ENGINES
        self.assertIn(saved_analysis_engine, expected_analysis_engines)
        remove_key_if_present(saved_trace_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.ANALYSIS_ENGINE])
        remove_key_if_present(comparison_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.ANALYSIS_ENGINE])

        # The usage of multiprocessing
        saved_use_multiprocessing = saved_trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.MULTIPROCESSING]
        self.assertIsInstance(saved_use_multiprocessing, bool)
        remove_key_if_present(saved_trace_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.MULTIPROCESSING])
        remove_key_if_present(comparison_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.MULTIPROCESSING])

        # The number of free cores left to the system
        saved_free_cores = saved_trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.FREE_CORES]
        self.assertIsInstance(saved_free_cores, int)
        self.assertTrue(saved_free_cores >= 0)
        remove_key_if_present(saved_trace_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.FREE_CORES])
        remove_key_if_present(comparison_dict,
                              [TraceData.PARAMETERS,
                               ExplorationParameters.FREE_CORES])

        # Remove the computation time of each explored attribute set also
        for explored_attr_set_info in comparison_dict[TraceData.EXPLORATION]:
            remove_key_if_present(explored_attr_set_info, TraceData.TIME)
        for explored_attr_set_info in saved_trace_dict[TraceData.EXPLORATION]:
            remove_key_if_present(explored_attr_set_info, TraceData.TIME)

        # If we do not want to check the exploration
        if not check_exploration:
            remove_key_if_present(saved_trace_dict, TraceData.EXPLORATION)
            remove_key_if_present(comparison_dict, TraceData.EXPLORATION)

        # Compare the two dictionaries
        self.assertDictEqual(saved_trace_dict, comparison_dict)

        # Remove the exploration trace
        remove(self._trace_path)

    def test_save_trace(self):
        # Run the exploration
        self._exploration.run()
        self._check_save_trace()

    def test_save_trace_asynchronous(self):
        # Run the exploration
        process = self._exploration.run_asynchronous()
        process.join()  # Wait for the process to end
        self._check_save_trace()


class TestExplorationMultiprocessing(TestExploration):

    def setUp(self):
        # If we use the modin engine, we ignore the multiprocessing test as it
        # is incompatible with modin
        #  if params.get('DataAnalysis', 'engine') == 'modin.pandas':
        #    self.skipTest('The data analysis modin.pandas is not supported')

        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = DummyExploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        params.set('Multiprocessing', 'explorations', 'true')


if __name__ == '__main__':
    unittest.main()
