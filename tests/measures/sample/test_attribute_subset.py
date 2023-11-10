#!/usr/bin/python3
"""Test module of the brfast.measures.distinguishability.entropy module."""

import unittest
from itertools import product
from os import remove
from typing import Set

from brfast.data.attribute import AttributeSet
from brfast.measures.sample.attribute_subset import AttributeSetSample
from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        NON_EXISTENT_ATTRIBUTE)

CSV_RESULT_PATH = 'sample_analysis_csv_result.csv'
SAMPLE_SIZE = 3
SAMPLE_SIZE_INCREASE = 5
WONT_COMPUTE = [()]


class TestAttributeSetSample(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._sample_size = SAMPLE_SIZE
        self._csv_result_path = CSV_RESULT_PATH

    def check_sample_result(self, possible_values: Set[tuple]):
        attribute_set_sample_analysis = AttributeSetSample(
            self._dataset, self._attribute_set, self._sample_size)
        attribute_set_sample_analysis.execute()
        analysis_result = attribute_set_sample_analysis.result
        first_fingerprint = next(iter(analysis_result.values()))
        expected_sample_size = min(self._sample_size,
                                   len(self._dataset.dataframe))
        self.assertEqual(len(first_fingerprint), len(self._attribute_set))
        self.assertEqual(expected_sample_size, len(analysis_result))
        for sample_id, sample_fingerprint in analysis_result.items():
            self.assertIn(sample_fingerprint, possible_values)

    def test_wrong_sample_size(self):
        with self.assertRaises(AttributeError):
            wrong_sample_size = 0
            AttributeSetSample(self._dataset, self._attribute_set,
                               wrong_sample_size)
        with self.assertRaises(AttributeError):
            wrong_sample_size = -3
            AttributeSetSample(self._dataset, self._attribute_set,
                               wrong_sample_size)

    def test_empty_dataset_and_empty_attribute_set(self):
        self._dataset = DummyEmptyDataset()
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_empty_attribute_set(self):
        self._attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_non_existent_attribute(self):
        self._attribute_set.add(NON_EXISTENT_ATTRIBUTE)
        with self.assertRaises(KeyError):
            self.check_sample_result(WONT_COMPUTE)

    def test_first_attribute_only(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0]])
        possible_values = set(product(self._dataset.DATAS[ATTRIBUTES[0].name]))
        self.check_sample_result(possible_values)

    def test_second_attribute_only(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[1]])
        possible_values = set(product(self._dataset.DATAS[ATTRIBUTES[1].name]))
        self.check_sample_result(possible_values)

    def test_third_attribute_only(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[2]])
        possible_values = set(product(self._dataset.DATAS[ATTRIBUTES[2].name]))
        self.check_sample_result(possible_values)

    def test_two_attributes(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0], ATTRIBUTES[1]])
        first_attribute_values = set(self._dataset.DATAS[ATTRIBUTES[0].name])
        second_attribute_values = set(self._dataset.DATAS[ATTRIBUTES[1].name])
        possible_values = set(product(
            first_attribute_values, second_attribute_values))
        self.check_sample_result(possible_values)

    def test_all_the_attributes(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        first_attribute_values = set(self._dataset.DATAS[ATTRIBUTES[0].name])
        second_attribute_values = set(self._dataset.DATAS[ATTRIBUTES[1].name])
        third_attribute_values = set(self._dataset.DATAS[ATTRIBUTES[2].name])
        possible_values = set(product(
            first_attribute_values, second_attribute_values,
            third_attribute_values))
        self.check_sample_result(possible_values)

    def test_first_attribute_only_higher_sample_size(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0]])
        self._sample_size = len(self._dataset.dataframe) + SAMPLE_SIZE_INCREASE
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_two_attributes_higher_sample_size(self):
        self._attribute_set = AttributeSet([ATTRIBUTES[0], ATTRIBUTES[1]])
        self._sample_size = len(self._dataset.dataframe) + SAMPLE_SIZE_INCREASE
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_all_the_attributes_higher_sample_size(self):
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._sample_size = len(self._dataset.dataframe) + SAMPLE_SIZE_INCREASE
        with self.assertRaises(ValueError):
            self.check_sample_result(WONT_COMPUTE)

    def test_save_csv_result(self):
        attribute_set_sample_analysis = AttributeSetSample(
            self._dataset, self._attribute_set, self._sample_size)
        attribute_set_sample_analysis.execute()
        attribute_set_sample_analysis.save_csv_result(self._csv_result_path)
        remove(self._csv_result_path)


if __name__ == '__main__':
    unittest.main()
