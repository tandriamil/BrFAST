#!/usr/bin/python3
"""Test module of the abtract classes for the measures."""

import unittest
from os import path, remove
from typing import Any, List

from brfast.data.attribute import AttributeSet
from brfast.measures import Analysis, SensitivityMeasure, UsabilityCostMeasure
from tests.data import DummyCleanDataset

CSV_RESULT_PATH = 'dummy_analysis_csv_result.csv'


class TestSensitivityMeasure(unittest.TestCase):

    def setUp(self):
        self._sensitivity_measure = SensitivityMeasure()

    def test_evaluate_abstract(self):
        with self.assertRaises(NotImplementedError):
            self._sensitivity_measure.evaluate(AttributeSet())

    def test_repr(self):
        self.assertIsInstance(repr(self._sensitivity_measure), str)


class TestUsabilityCostMeasure(unittest.TestCase):

    def setUp(self):
        self._usability_cost_measure = UsabilityCostMeasure()

    def test_evaluate_abstract(self):
        with self.assertRaises(NotImplementedError):
            self._usability_cost_measure.evaluate(AttributeSet())

    def test_repr(self):
        self.assertIsInstance(repr(self._usability_cost_measure), str)


class TestAnalysis(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._csv_result_path = CSV_RESULT_PATH
        self._analysis = DummyAnalysis(self._dataset)

    def test_execute(self):
        self._analysis.execute()

    def test_result_property(self):
        empty_dictionary = {}
        self.assertDictEqual(empty_dictionary, self._analysis.result)
        with self.assertRaises(AttributeError):
            self._analysis.result = {'forbidden_action': 'readonly'}
        # After the execution
        self._analysis.execute()
        expected_result = self._analysis.DATA
        self.assertDictEqual(expected_result, self._analysis.result)

    def test_save_csv_result(self):
        # After the execution
        self._analysis.execute()
        self._analysis.save_csv_result(self._csv_result_path)
        self.assertTrue(path.isfile(self._csv_result_path))
        remove(self._csv_result_path)


class DummyAnalysis(Analysis):

    DATA = {'dummy_result': 42}

    def execute(self):
        """Execute the analysis."""
        self._result = self.DATA

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = []
        for key, value in self._result.items():
            row_list.append([key, value])
        return row_list


if __name__ == '__main__':
    unittest.main()
