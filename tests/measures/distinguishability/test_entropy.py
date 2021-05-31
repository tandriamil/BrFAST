#!/usr/bin/python3
"""Test module of the brfast.measures.distinguishability.entropy module."""

import unittest
from math import log2
from os import remove

from brfast.data.attribute import Attribute, AttributeSet
from brfast.measures.distinguishability.entropy import (
    attribute_set_entropy, AttributeSetEntropy, ENTROPY_RESULT,
    MAXIMUM_ENTROPY_RESULT, NORMALIZED_ENTROPY_RESULT)

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        UNEXISTENT_ATTRIBUTE)

CSV_RESULT_PATH = 'entropy_analysis_csv_result.csv'
WONT_COMPUTE = 0.0


class TestAttributeSetEntropyFunction(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._df_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        self._attribute_set = AttributeSet(ATTRIBUTES)

    def check_entropy_result(self, expected_entropy: float):
        computed_entropy = attribute_set_entropy(self._df_one_fp_per_browser,
                                                 self._attribute_set)
        self.assertAlmostEqual(expected_entropy, computed_entropy)

    def test_empty_dataset_and_empty_attribute_set(self):
        self._dataset = DummyEmptyDataset()
        self._df_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        self._df_one_fp_per_browser = (
            self._dataset.get_df_w_one_fp_per_browser())
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_empty_attribute_set(self):
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_always_the_same_value(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[2]])
        self.check_entropy_result(0.0)

    def test_in_between_entropy(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0]])
        expected_entropy = -1 * ((1/5)*log2(1/5) + (2/5)*log2(2/5)
                                 + (2/5)*log2(2/5))
        self.check_entropy_result(expected_entropy)

    def test_unique_values(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[1]])
        expected_entropy = log2(len(self._dataset.dataframe))
        self.check_entropy_result(expected_entropy)


class TestAttributeSetEntropy(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._csv_result_path = CSV_RESULT_PATH

    def check_entropy_result(self, expected_entropy: float):
        maximum_entropy = log2(len(self._dataset.dataframe))
        attribute_set_entropy_analysis = AttributeSetEntropy(
            self._dataset, self._attribute_set)
        attribute_set_entropy_analysis.execute()
        analysis_result = attribute_set_entropy_analysis.result
        expected_result = {
            ENTROPY_RESULT: expected_entropy,
            MAXIMUM_ENTROPY_RESULT: maximum_entropy,
            NORMALIZED_ENTROPY_RESULT: expected_entropy/maximum_entropy
        }
        for result_name, expected_value in expected_result.items():
            self.assertAlmostEqual(analysis_result[result_name],
                                   expected_value)

    def test_empty_dataset_and_empty_attribute_set(self):
        self._dataset = DummyEmptyDataset()
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_empty_attribute_set(self):
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_unexistent_attribute(self):
        self._attribute_set.add(UNEXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            self.check_entropy_result(WONT_COMPUTE)

    def test_in_between_entropy(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0]])
        expected_entropy = -1 * ((1/5)*log2(1/5) + (2/5)*log2(2/5)
                                 + (2/5)*log2(2/5))
        self.check_entropy_result(expected_entropy)

    def test_always_the_same_value(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[2]])
        self.check_entropy_result(0.0)

    def test_unique_values(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[1]])
        maximum_entropy = log2(len(self._dataset.dataframe))
        self.check_entropy_result(maximum_entropy)

    def test_save_csv_result(self):
        attribute_set_entropy_analysis = AttributeSetEntropy(
            self._dataset, self._attribute_set)
        attribute_set_entropy_analysis.execute()
        attribute_set_entropy_analysis.save_csv_result(self._csv_result_path)
        remove(self._csv_result_path)


if __name__ == '__main__':
    unittest.main()
