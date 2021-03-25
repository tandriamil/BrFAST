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
from brfast.exploration.entropy import _get_attributes_entropy, Entropy
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        DummyFingerprintDataset)
from tests.exploration import SENSITIVITY_THRESHOLD, TRACE_FILENAME
from tests.measures import DummySensitivity, DummyUsabilityCostMeasure

EXPECTED_TRACE_PATH = 'assets/expected_trace_entropy.json'


class TestGetAttributesEntropy(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset_path = path.abspath(__file__)
        self._dataset = DummyCleanDataset(self._dataset_path)

    def test_get_attributes_entropy(self):
        expected_result = {
            ATTRIBUTES[0]: -1 * ((1/5)*log2(1/5) + (2/5)*log2(2/5)
                                 + (2/5)*log2(2/5)),
            ATTRIBUTES[1]: log2(len(self._dataset.dataframe)),
            ATTRIBUTES[2]: 0.0
        }
        result = _get_attributes_entropy(self._dataset, self._attribute_set)
        # Needed due to float precision
        for attribute in self._attribute_set:
            self.assertAlmostEqual(result[attribute],
                                   expected_result[attribute])

    def test_get_attributes_entropy_empty_attribute_set(self):
        expected_result = {}
        result = _get_attributes_entropy(self._dataset, AttributeSet())
        self.assertDictEqual(result, expected_result)

    def test_get_attributes_entropy_empty_dataset(self):
        empty_dataset = DummyEmptyDataset(self._dataset_path)
        with self.assertRaises(KeyError):  # Missing attribute
            _get_attributes_entropy(empty_dataset, self._attribute_set)

    def test_get_attributes_entropy_empty_attribute_set_and_dataset(self):
        expected_result = {}
        empty_dataset = DummyEmptyDataset(self._dataset_path)
        result = _get_attributes_entropy(empty_dataset, AttributeSet())
        self.assertDictEqual(result, expected_result)


class TestEntropy(unittest.TestCase):

    def setUp(self):
        self._dataset_path = path.abspath(__file__)  # Needed to exist
        self._dataset = DummyCleanDataset(self._dataset_path)
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME

    def test_repr(self):
        exploration = Entropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        self.assertIsInstance(str(exploration), str)

    def test_parameters(self):
        exploration = Entropy(
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
        exploration = Entropy(
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
        unreachable_exploration = Entropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold)
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.run()

    def test_run(self):
        # Initialize and run the exploration
        exploration = Entropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        exploration.run()

        # Check that the solution is the one expected
        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        self.assertEqual(exploration.get_solution(), expected_solution)

        # Check that the satisfying attributes are the right ones
        expected_satisfying_attribute_sets = {
            AttributeSet(ATTRIBUTES), AttributeSet(expected_solution)}
        self.assertEqual(exploration.get_satisfying_attribute_sets(),
                         expected_satisfying_attribute_sets)

    def test_save_trace(self):
        # Initialize and run the exploration
        exploration = Entropy(
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
