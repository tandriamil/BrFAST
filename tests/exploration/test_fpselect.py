#!/usr/bin/python3
"""Test module of the exploration module of BrFAST.

The data used for the tests is a simple simulation of the lattice example of
our FPSelect paper.
"""

import importlib
import json
import unittest
from math import log2
from os import path, remove
from pathlib import PurePath
from typing import Any, Dict

from brfast.config import ANALYSIS_ENGINES
from brfast.data.attribute import AttributeSet
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, State, TraceData)
from brfast.exploration.fpselect import FPSelect, FPSelectParameters
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

from tests.data import ATTRIBUTES, DummyCleanDataset
from tests.exploration import SENSITIVITY_THRESHOLD, TRACE_FILENAME
from tests.exploration.test_exploration import TestExploration
from tests.measures import DummySensitivity, DummyUsabilityCostMeasure

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
pd = importlib.import_module(params['DataAnalysis']['engine'])

TRACES_DIRECTORY = 'assets/traces'
EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_ON = '/'.join(
    [TRACES_DIRECTORY, 'expected_trace_fpselect_multipath_pruning_on.json'])
EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_OFF = '/'.join(
    [TRACES_DIRECTORY, 'expected_trace_fpselect_multipath_pruning_off.json'])
EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_ON = '/'.join(
    [TRACES_DIRECTORY, 'expected_trace_fpselect_singlepath_pruning_on.json'])
EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_OFF = '/'.join(
    [TRACES_DIRECTORY, 'expected_trace_fpselect_singlepath_pruning_off.json'])
MULTI_EXPLR_PATHS = 2
PRUNING_ON = True
PRUNING_OFF = False


# ======= FPSelect with a single process and using the DummyCleanDataset ======
class TestFPSelectSinglePathPruningOn(TestExploration):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_ON
        self._explored_paths = 1
        self._pruning = PRUNING_ON
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'false')

    def test_exploration_base_class(self):
        pass  # This selection method defines the run method

    def test_parameters(self):
        additional_parameters = {
            FPSelectParameters.EXPLORED_PATHS: self._explored_paths,
            FPSelectParameters.PRUNING: self._pruning}
        self.check_parameters(additional_parameters)

    def test_run_sensitivity_unreachable(self):
        unreachable_sensitivity_threshold = 0.0
        unreachable_exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        with self.assertRaises(SensitivityThresholdUnreachable):
            unreachable_exploration.run()

    def test_run_asynchronous_sensitivity_unreachable(self):
        unreachable_sensitivity_threshold = 0.0
        unreachable_exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, unreachable_sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
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
                       expected_explored_attribute_sets,
                       check_exploration=False)

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
                       expected_explored_attribute_sets,
                       check_exploration=False)

    def test_wrong_number_of_explored_paths(self):
        with self.assertRaises(AttributeError):
            unaccepted_number_of_explored_paths = 0
            wrong_number_of_explored_paths = FPSelect(
                self._sensitivity_measure, self._usability_cost_measure,
                self._dataset, self._sensitivity_threshold,
                explored_paths=unaccepted_number_of_explored_paths,
                pruning=self._pruning)
        with self.assertRaises(AttributeError):
            unaccepted_number_of_explored_paths = -3
            wrong_number_of_explored_paths = FPSelect(
                self._sensitivity_measure, self._usability_cost_measure,
                self._dataset, self._sensitivity_threshold,
                explored_paths=unaccepted_number_of_explored_paths,
                pruning=self._pruning)

    def test_save_trace(self):
        # Run the exploration
        self._exploration.run()
        self._check_save_trace(check_exploration=False)

    def test_save_trace_asynchronous(self):
        # Run the exploration
        process = self._exploration.run_asynchronous()
        process.join()  # Wait for the process to end
        self._check_save_trace(check_exploration=False)


class TestFPSelectSinglePathPruningOff(TestFPSelectSinglePathPruningOn):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_OFF
        self._explored_paths = 1
        self._pruning = PRUNING_OFF
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'false')


class TestFPSelectMultipathPruningOn(TestFPSelectSinglePathPruningOn):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_ON
        self._explored_paths = MULTI_EXPLR_PATHS
        self._pruning = PRUNING_ON
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'false')


class TestFPSelectMultipathPruningOff(TestFPSelectSinglePathPruningOn):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._sensitivity_measure = DummySensitivity()
        self._usability_cost_measure = DummyUsabilityCostMeasure()
        self._sensitivity_threshold = SENSITIVITY_THRESHOLD
        self._trace_path = TRACE_FILENAME
        self._expected_trace_path = EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_OFF
        self._pruning = PRUNING_OFF
        self._explored_paths = MULTI_EXPLR_PATHS
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'false')
# ======= FPSelect with a single process and using the DummyCleanDataset ======


# ========== FPSelect using multiprocessing and the DummyCleanDataset =========
class TestFPSelectSinglePathPruningOnMultiprocessing(TestFPSelectSinglePathPruningOn):

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
        self._expected_trace_path = EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_ON
        self._explored_paths = 1
        self._pruning = PRUNING_ON
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'true')


class TestFPSelectSinglePathPruningOffMultiprocessing(TestFPSelectSinglePathPruningOnMultiprocessing):

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
        self._expected_trace_path = EXPECTED_TRACE_PATH_SINGLEPATH_PRUNING_OFF
        self._explored_paths = 1
        self._pruning = PRUNING_OFF
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'true')


class TestFPSelectMultipathPruningOnMultiprocessing(TestFPSelectSinglePathPruningOnMultiprocessing):

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
        self._expected_trace_path = EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_ON
        self._explored_paths = MULTI_EXPLR_PATHS
        self._pruning = PRUNING_ON
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'true')


class TestFPSelectMultipathPruningOffMultiprocessing(TestFPSelectSinglePathPruningOnMultiprocessing):

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
        self._expected_trace_path = EXPECTED_TRACE_PATH_MULTIPATH_PRUNING_OFF
        self._pruning = PRUNING_OFF
        self._explored_paths = MULTI_EXPLR_PATHS
        self._exploration = FPSelect(
            self._sensitivity_measure, self._usability_cost_measure,
            self._dataset, self._sensitivity_threshold,
            explored_paths=self._explored_paths, pruning=self._pruning)
        params.set('Multiprocessing', 'explorations', 'true')
# ========== FPSelect using multiprocessing and the DummyCleanDataset =========


if __name__ == '__main__':
    unittest.main()
