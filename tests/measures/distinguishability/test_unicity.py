#!/usr/bin/python3
"""Test module of the brfast.measures.distinguishability.entropy module."""

import unittest
from os import remove

from brfast.data.attribute import AttributeSet
from brfast.measures.distinguishability.unicity import (
    AttributeSetUnicity, TOTAL_BROWSERS_RESULT, UNIQUE_FPS_RESULT,
    UNICITY_RATE_RESULT)
from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        NON_EXISTENT_ATTRIBUTE)

CSV_RESULT_PATH = 'unicity_analysis_csv_result.csv'
WONT_COMPUTE = 0


class TestAttributeSetUnicity(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._csv_result_path = CSV_RESULT_PATH

    def check_unicity_result(self, expected_unique_fps: int):
        total_browsers = len(self._dataset.dataframe)
        attribute_set_unicity_analysis = AttributeSetUnicity(
            self._dataset, self._attribute_set)
        attribute_set_unicity_analysis.execute()
        analysis_result = attribute_set_unicity_analysis.result
        expected_result = {
            UNIQUE_FPS_RESULT: expected_unique_fps,
            TOTAL_BROWSERS_RESULT: total_browsers,
            UNICITY_RATE_RESULT: expected_unique_fps/total_browsers
        }
        for result_name, expected_value in expected_result.items():
            self.assertAlmostEqual(analysis_result[result_name],
                                   expected_value)

    def test_empty_dataset_and_empty_attribute_set(self):
        self._dataset = DummyEmptyDataset()
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_unicity_result(WONT_COMPUTE)

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        with self.assertRaises(ValueError):
            self.check_unicity_result(WONT_COMPUTE)

    def test_empty_attribute_set(self):
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_unicity_result(WONT_COMPUTE)

    def test_non_existent_attribute(self):
        self._attribute_set.add(NON_EXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            self.check_unicity_result(WONT_COMPUTE)

    def test_in_between_entropy(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0]])
        self.check_unicity_result(1)

    def test_always_the_same_value(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[2]])
        self.check_unicity_result(0)

    def test_unique_values(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[1]])
        total_browsers = len(self._dataset.dataframe)
        self.check_unicity_result(total_browsers)

    def test_save_csv_result(self):
        attribute_set_unicity_analysis = AttributeSetUnicity(
            self._dataset, self._attribute_set)
        attribute_set_unicity_analysis.execute()
        attribute_set_unicity_analysis.save_csv_result(self._csv_result_path)
        remove(self._csv_result_path)


if __name__ == '__main__':
    unittest.main()
