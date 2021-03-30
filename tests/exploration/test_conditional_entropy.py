#!/usr/bin/python3
"""Test module of the exploration module of BrFAST."""

import json
import unittest
from math import log2
from os import path, remove
from typing import Any, Dict

from brfast.data import AttributeSet
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, State, TraceData)
from brfast.exploration.conditional_entropy import (
    _get_best_conditional_entropic_attribute, ConditionalEntropy)
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        DummyFingerprintDataset)
from tests.exploration import SENSITIVITY_THRESHOLD, TRACE_FILENAME
from tests.measures import DummySensitivity, DummyUsabilityCostMeasure

EXPECTED_TRACE_PATH = 'assets/expected_trace_conditional_entropy.json'


class TestGetBestConditionalEntropicAttribute(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset_path = path.abspath(__file__)
        self._dataset = DummyCleanDataset(self._dataset_path)

    def test_get_best_entropic_attribute(self):
        # The order is 1 (unique values), then 0 (some collisions), then
        # 2 (the same value for each browser)
        first_best = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=AttributeSet(),
            candidate_attributes=self._attribute_set)
        self.assertEqual(first_best, ATTRIBUTES[1])

        second_best = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=AttributeSet({ATTRIBUTES[1]}),
            candidate_attributes=self._attribute_set)
        self.assertEqual(second_best, ATTRIBUTES[0])

        third_best = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=AttributeSet({ATTRIBUTES[1],
                                                            ATTRIBUTES[0]}),
            candidate_attributes=self._attribute_set)
        self.assertEqual(third_best, ATTRIBUTES[2])

        no_more_available = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=AttributeSet({
                ATTRIBUTES[1], ATTRIBUTES[0], ATTRIBUTES[2]}),
            candidate_attributes=self._attribute_set)
        self.assertIsNone(no_more_available)

    def test_get_best_entropic_attribute_every_attribute_already_taken(self):
        result = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=self._attribute_set,
            candidate_attributes=self._attribute_set)
        self.assertIsNone(result)

    def test_get_best_entropic_attribute_empty_attribute_set(self):
        result = _get_best_conditional_entropic_attribute(
            self._dataset, current_attributes=self._attribute_set,
            candidate_attributes=AttributeSet())
        self.assertIsNone(result)

    def test_get_best_entropic_attribute_empty_dataset(self):
        empty_dataset = DummyEmptyDataset(self._dataset_path)
        with self.assertRaises(KeyError):  # Missing attribute
            _get_best_conditional_entropic_attribute(
                empty_dataset,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)

    def test_get_best_entropic_attribute_empty_attribute_set_and_dataset(self):
        empty_dataset = DummyEmptyDataset(self._dataset_path)
        with self.assertRaises(KeyError):  # Missing attribute
            _get_best_conditional_entropic_attribute(
                empty_dataset,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)


class TestConditionalEntropy(unittest.TestCase):

    def setUp(self):
        self._dataset_path = path.abspath(__file__)  # Needed to exist
        self._dataset = DummyCleanDataset(self._dataset_path)
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME

    def test_repr(self):
        exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        self.assertIsInstance(str(exploration), str)

    def test_parameters(self):
        exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        expected_parameters = {
            ExplorationParameters.METHOD: exploration.__class__.__name__,
            ExplorationParameters.SENSITIVITY_MEASURE: str(
                self._sensitivity_measure),
            ExplorationParameters.USABILITY_COST_MEASURE: str(
                self._usability_cost_measure),
            ExplorationParameters.DATASET: str(self._dataset),
            ExplorationParameters.SENSITIVITY_THRESHOLD: (
                self._sensitivity_threshold)
        }
        self.assertDictEqual(exploration.parameters, expected_parameters)
        with self.assertRaises(AttributeError):
            exploration.parameters = {'refused_as_it_is': 'readonly'}

    def test_exploration_not_ran(self):
        exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        with self.assertRaises(ExplorationNotRun):
            exploration.get_solution()
        with self.assertRaises(ExplorationNotRun):
            exploration.get_satisfying_attribute_sets()
        with self.assertRaises(ExplorationNotRun):
            exploration.save_exploration_trace(self._trace_path)

    def test_run_sensitivity_unreachable(self):
        unreachable_sensitivity_threshold = 0.0
        unreachable_exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold)
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.run()

    def test_run(self):
        # Initialize and run the exploration
        exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        exploration.run()

        # Check that the solution is the one expected
        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        self.assertEqual(exploration.get_solution(), expected_solution)

        # Check that the satisfying attributes are the right ones
        expected_satisfying_attribute_sets = {
            AttributeSet(ATTRIBUTES), expected_solution}
        self.assertEqual(exploration.get_satisfying_attribute_sets(),
                         expected_satisfying_attribute_sets)

    def test_save_trace(self):
        # Initialize and run the exploration
        exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        exploration.run()

        # Save the exploration trace
        exploration.save_exploration_trace(self._trace_path)

        # Load the comparison file as a json dictionary
        tests_module_path = '/'.join(self._dataset_path.split('/')[:-2])
        comparison_trace_path = f'{tests_module_path}/{EXPECTED_TRACE_PATH}'
        with open(comparison_trace_path, 'r') as comparison_file:
            comparison_dict = json.load(comparison_file)

        # Load the saved trace file as a json dictionary
        with open(self._trace_path, 'r') as saved_trace_file:
            saved_trace_dict = json.load(saved_trace_file)

        # Remove the dynamic start_time of each of these files
        del comparison_dict[TraceData.RESULT][TraceData.START_TIME]
        del saved_trace_dict[TraceData.RESULT][TraceData.START_TIME]

        # Check and then remove the dataset information which contains its path
        # that includes the path of the dataset (which is its file in fact)
        comparison_dataset_info = comparison_dict[TraceData.PARAMETERS][
            ExplorationParameters.DATASET]
        # NOTE The comparison dict that is read is given as a file and contains
        #      the path of my own laptop. No need to verify it.
        # self.assertEqual(comparison_dataset_info, str(self._dataset))
        del comparison_dict[TraceData.PARAMETERS][
            ExplorationParameters.DATASET]
        saved_trace_dataset_info = saved_trace_dict[TraceData.PARAMETERS][
                ExplorationParameters.DATASET]
        self.assertEqual(saved_trace_dataset_info, str(self._dataset))
        del saved_trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.DATASET]

        # Remove the computation time of each explored attribute set also
        for explored_attr_set_info in comparison_dict[TraceData.EXPLORATION]:
            del explored_attr_set_info[TraceData.TIME]
        for explored_attr_set_info in saved_trace_dict[TraceData.EXPLORATION]:
            del explored_attr_set_info[TraceData.TIME]

        # Compare the two dictionaries
        self.assertDictEqual(saved_trace_dict, comparison_dict)

        # Remove the exploration trace
        remove(self._trace_path)


if __name__ == '__main__':
    unittest.main()
