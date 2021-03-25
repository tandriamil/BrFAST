#!/usr/bin/python3
"""Test module of the exploration module of BrFAST."""

import json
import unittest
from typing import Any, Dict
from os import path, remove

import pandas as pd
from sortedcontainers import SortedDict

from brfast.data import (Attribute, AttributeSet, FingerprintDataset,
                         MetadataField)
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, State, TraceData)

from tests.data import ATTRIBUTES, DummyFingerprintDataset
from tests.exploration import (DUMMY_PARAMETER_FIELD, DummyExploration,
                               SENSITIVITY_THRESHOLD, TRACE_FILENAME)
from tests.measures import (DummySensitivity, DummyUsabilityCostMeasure,
                            SENSITIVITIES, TOTAL_COST_FIELD, USABILITIES)

EXPECTED_TRACE_PATH = 'assets/expected_trace_dummy_exploration.json'


class TestExploration(unittest.TestCase):

    def setUp(self):
        self._dataset_path = path.abspath(__file__)  # Needed to exist
        self._dataset = DummyFingerprintDataset(self._dataset_path)
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME

    def test_repr(self):
        exploration = DummyExploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        self.assertIsInstance(str(exploration), str)

    def test_exploration_base_class(self):
        exploration = Exploration(
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
        with self.assertRaises(NotImplementedError):
            # _search_for_solution is abstract and not defined for Exploration
            exploration.run()

    def test_parameters(self):
        exploration = DummyExploration(
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
                self._sensitivity_threshold),
            DUMMY_PARAMETER_FIELD: 42
        }
        self.assertDictEqual(exploration.parameters, expected_parameters)
        with self.assertRaises(AttributeError):
            exploration.parameters = {'refused_as_it_is': 'readonly'}

    def test_exploration_not_ran(self):
        exploration = DummyExploration(
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
        unreachable_exploration = DummyExploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold)
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.run()

    def test_run(self):
        # Initialize and run the exploration
        exploration = DummyExploration(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        exploration.run()

        # Check that the solution is the one expected
        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        self.assertEqual(exploration.get_solution(), expected_solution)

        # Check that the satisfying attributes are the right ones
        expected_satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1], ATTRIBUTES[2]})}
        self.assertEqual(exploration.get_satisfying_attribute_sets(),
                         expected_satisfying_attribute_sets)

    def test_save_trace(self):
        # Initialize and run the exploration
        exploration = DummyExploration(
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
