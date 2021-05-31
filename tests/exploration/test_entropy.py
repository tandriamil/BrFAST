#!/usr/bin/python3
"""Test module of the exploration module of BrFAST."""

import importlib
import json
import unittest
from math import log2
from os import path, remove
from pathlib import PurePath
from typing import Any, Dict

from brfast.config import ANALYSIS_ENGINES
from brfast.data.attribute import Attribute, AttributeSet
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, State, TraceData)
from brfast.exploration.entropy import (
    _compute_attribute_entropy, _get_attributes_entropy, Entropy)
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        UNEXISTENT_ATTRIBUTE)
from tests.exploration import (SENSITIVITY_THRESHOLD, TRACE_FILENAME,
                               MODIN_ANALYSIS_ENGINES)
from tests.exploration.test_exploration import TestExploration
from tests.measures import DummySensitivity, DummyUsabilityCostMeasure

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
pd = importlib.import_module(params['DataAnalysis']['engine'])

EXPECTED_TRACE_PATH = 'assets/traces/expected_trace_entropy.json'


class TestGetAttributesEntropy(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset = DummyCleanDataset()

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

    def test_get_attributes_entropy_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            _get_attributes_entropy(self._dataset, self._attribute_set)

    def test_get_attributes_entropy_empty_attribute_set(self):
        expected_result = {}
        result = _get_attributes_entropy(self._dataset, AttributeSet())
        self.assertDictEqual(result, expected_result)

    def test_get_attributes_entropy_empty_dataset(self):
        empty_dataset = DummyEmptyDataset()
        with self.assertRaises(ValueError):
            _get_attributes_entropy(empty_dataset, self._attribute_set)

    def test_get_attributes_entropy_empty_attribute_set_and_dataset(self):
        expected_result = {}
        empty_dataset = DummyEmptyDataset()
        result = _get_attributes_entropy(empty_dataset, AttributeSet())
        self.assertDictEqual(result, expected_result)


class TestComputeAttributeEntropy(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset = DummyCleanDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())

    def test_compute_attribute_entropy(self):
        expected_result = {
            ATTRIBUTES[0]: -1 * ((1/5)*log2(1/5) + (2/5)*log2(2/5)
                                 + (2/5)*log2(2/5)),
            ATTRIBUTES[1]: log2(len(self._dataset.dataframe)),
            ATTRIBUTES[2]: 0.0
        }
        attributes_entropy = _compute_attribute_entropy(
            self._df_w_one_fp_per_browser, self._attribute_set)
        # Needed due to float precision
        for attribute, entropy in attributes_entropy.items():
            self.assertAlmostEqual(entropy, expected_result[attribute])

    def test_get_attributes_entropy_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            attributes_entropy = _compute_attribute_entropy(
                self._df_w_one_fp_per_browser, self._attribute_set)

    def test_get_attributes_entropy_empty_attribute_set(self):
        attributes_entropy = _compute_attribute_entropy(
            self._df_w_one_fp_per_browser, AttributeSet())
        self.assertFalse(attributes_entropy)

    def test_get_attributes_entropy_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        with self.assertRaises(ValueError):
            attributes_entropy = _compute_attribute_entropy(
                self._df_w_one_fp_per_browser, self._attribute_set)

    def test_get_attributes_entropy_empty_attribute_set_and_dataset(self):
        self._dataset = DummyEmptyDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        attributes_entropy = _compute_attribute_entropy(
            self._df_w_one_fp_per_browser, AttributeSet())
        self.assertFalse(attributes_entropy)


class TestEntropy(TestExploration):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = Entropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        params.set('Multiprocessing', 'explorations', 'false')

    def test_exploration_base_class(self):
        pass  # This selection method defines the run method

    def test_parameters(self):
        self.check_parameters()

    def test_run(self):
        # Run the exploration
        self._exploration.run()

        # Load the comparison file as a json dictionary
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        comparison_trace_path = tests_module_path.joinpath(
            self._expected_trace_path)
        with open(comparison_trace_path, 'r') as comparison_file:
            comparison_dict = json.load(comparison_file)
        expected_explored_attribute_sets = comparison_dict[
            TraceData.EXPLORATION]

        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        expected_satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1], ATTRIBUTES[2]})}
        self.check_run(expected_solution, expected_satisfying_attribute_sets,
                       expected_explored_attribute_sets)

    def test_run_asynchronous(self):
        # Run the exploration
        process = self._exploration.run_asynchronous()
        process.join()  # Wait for the process to end

        # Load the comparison file as a json dictionary
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        comparison_trace_path = tests_module_path.joinpath(
            self._expected_trace_path)
        with open(comparison_trace_path, 'r') as comparison_file:
            comparison_dict = json.load(comparison_file)
        expected_explored_attribute_sets = comparison_dict[
            TraceData.EXPLORATION]

        expected_solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})
        expected_satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1], ATTRIBUTES[2]})}
        self.check_run(expected_solution, expected_satisfying_attribute_sets,
                       expected_explored_attribute_sets)


class TestEntropyMultiprocessing(TestEntropy):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = Entropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        params.set('Multiprocessing', 'explorations', 'true')


if __name__ == '__main__':
    unittest.main()
