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
from brfast.exploration.conditional_entropy import (
    _get_best_conditional_entropic_attribute,
    _best_conditional_entropic_attribute, ConditionalEntropy)
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        UNEXISTENT_ATTRIBUTE)
from tests.exploration import (SENSITIVITY_THRESHOLD, TRACE_FILENAME,
                               MODIN_ANALYSIS_ENGINES)
from tests.exploration.test_entropy import TestExploration
from tests.measures import DummySensitivity, DummyUsabilityCostMeasure

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
pd = importlib.import_module(params['DataAnalysis']['engine'])

EXPECTED_TRACE_PATH = 'assets/traces/expected_trace_conditional_entropy.json'


class TestGetBestConditionalEntropicAttribute(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset = DummyCleanDataset()

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
            self._dataset, current_attributes=AttributeSet({ATTRIBUTES[0],
                                                            ATTRIBUTES[1]}),
            candidate_attributes=AttributeSet())
        self.assertIsNone(result)

    def test_get_best_entropic_attribute_empty_dataset(self):
        empty_dataset = DummyEmptyDataset()
        with self.assertRaises(ValueError):
            _get_best_conditional_entropic_attribute(
                empty_dataset,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)

    def test_get_best_entropic_attribute_empty_candidates_and_dataset(self):
        empty_dataset = DummyEmptyDataset()
        result = _get_best_conditional_entropic_attribute(
            empty_dataset, current_attributes=AttributeSet({ATTRIBUTES[0],
                                                            ATTRIBUTES[1]}),
            candidate_attributes=AttributeSet())
        self.assertIsNone(result)

    def test_get_best_entropic_attribute_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            _get_best_conditional_entropic_attribute(
                self._dataset,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)


class TestBestConditionalEntropic(unittest.TestCase):

    def setUp(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._dataset = DummyCleanDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())

    def test_best_conditional_entropic_attribute(self):
        # This will just take the first attribute which is sufficient as it has
        # unique values
        best_cond_ent_attr = _best_conditional_entropic_attribute(
            self._df_w_one_fp_per_browser, current_attributes=AttributeSet(),
            candidate_attributes=self._attribute_set)
        self.assertEqual(best_cond_ent_attr[0], ATTRIBUTES[1])

    def test_best_conditional_entropic_attribute_all_taken(self):
        best_cond_ent_attr = _best_conditional_entropic_attribute(
            self._df_w_one_fp_per_browser,
            current_attributes=self._attribute_set,
            candidate_attributes=self._attribute_set)
        self.assertIsNone(best_cond_ent_attr[0])

    def test_best_conditional_entropic_attribute_empty_attribute_set(self):
        best_cond_ent_attr = _best_conditional_entropic_attribute(
            self._df_w_one_fp_per_browser,
            current_attributes=AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            candidate_attributes=AttributeSet())
        self.assertIsNone(best_cond_ent_attr[0])

    def test_best_conditional_entropic_attribute_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        with self.assertRaises(ValueError):
            best_cond_ent_attr = _best_conditional_entropic_attribute(
                self._df_w_one_fp_per_browser,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)

    def test_best_conditional_entropic_attribute_empty_parameters(self):
        self._dataset = DummyEmptyDataset()
        self._df_w_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        best_cond_ent_attr = _best_conditional_entropic_attribute(
            self._df_w_one_fp_per_browser,
            current_attributes=AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            candidate_attributes=AttributeSet())
        self.assertIsNone(best_cond_ent_attr[0])

    def test_best_conditional_entropic_attribute_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            best_cond_ent_attr = _best_conditional_entropic_attribute(
                self._df_w_one_fp_per_browser,
                current_attributes=AttributeSet({ATTRIBUTES[0],
                                                 ATTRIBUTES[1]}),
                candidate_attributes=self._attribute_set)


class TestConditionalEntropy(TestExploration):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = ConditionalEntropy(
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


class TestConditionalEntropyMultiprocessing(TestConditionalEntropy):

    def setUp(self):
        # If we use the modin engine, we ignore the multiprocessing test as it
        # is incompatible with modin
        if params.get('DataAnalysis', 'engine') == 'modin.pandas':
            self.skipTest()

        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH
        self._exploration = ConditionalEntropy(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold)
        params.set('Multiprocessing', 'explorations', 'true')


if __name__ == '__main__':
    unittest.main()
