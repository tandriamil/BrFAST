#!/usr/bin/python3
"""Tests of the brfast.measures.usability_cost.memory module."""

import unittest
from os import path, remove
from statistics import mean

from brfast.data.attribute import AttributeSet
from brfast.measures.usability_cost.memory import (
    _compute_attribute_avg_size, AverageFingerprintSize)

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        DummyFingerprintDataset)

CSV_RESULT_PATH = 'test_memory.csv'


class TestComputeAttributeAverageSize(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._dataframe = self._dataset.dataframe
        self._attributes = AttributeSet(ATTRIBUTES)

    def _get_expected_result(self):
        expected_result = {}
        for attribute in self._attributes:
            expected_result[attribute] = mean(
                len(str(value))
                for value in self._dataset.DATAS[attribute.name])
        return expected_result

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        with self.assertRaises(KeyError):  # Attribute is not in the dataset
            _compute_attribute_avg_size(self._dataset.dataframe,
                                        self._attributes)

    def test_empty_attributes(self):
        self._attributes = AttributeSet({})
        attributes_avg_size = _compute_attribute_avg_size(
            self._dataframe, self._attributes)
        expected_result = self._get_expected_result()
        self.assertDictEqual(expected_result, attributes_avg_size)

    def test_empty_dataset_and_attributes(self):
        self._dataset = DummyEmptyDataset()
        self._dataframe = self._dataset.dataframe
        self._attributes = AttributeSet({})
        attributes_avg_size = _compute_attribute_avg_size(
            self._dataset, self._attributes)
        expected_result = self._get_expected_result()
        self.assertDictEqual(expected_result, attributes_avg_size)

    def test_clean_dataset(self):
        attributes_avg_size = _compute_attribute_avg_size(
            self._dataframe, self._attributes)
        expected_result = self._get_expected_result()
        self.assertDictEqual(expected_result, attributes_avg_size)

    def test_dummy_fingerprint_dataset(self):
        self._dataset = DummyFingerprintDataset()
        self._dataframe = self._dataset.dataframe
        attributes_avg_size = _compute_attribute_avg_size(
            self._dataframe, self._attributes)
        expected_result = self._get_expected_result()
        self.assertDictEqual(expected_result, attributes_avg_size)


class TestAverageFingerprintSize(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attributes_avg_size = {}

    def _check_result(self):
        attributes = self._dataset.candidate_attributes

        # Prepare the expected result
        expected_result = {}
        for attribute in attributes:
            expected_result[attribute] = mean(
                len(str(value))
                for value in self._dataset.DATAS[attribute.name])

        # Execute the analysis and check the obtained result
        analysis = AverageFingerprintSize(self._dataset)
        analysis.execute()
        self.assertDictEqual(expected_result, analysis.result)

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        self._check_result()

    def test_clean_dataset(self):
        self._dataset = DummyCleanDataset()
        self._check_result()

    def test_dummy_fingerprint_dataset(self):
        self._dataset = DummyFingerprintDataset()
        self._check_result()

    def test_save_csv_result(self):
        analysis = AverageFingerprintSize(self._dataset)
        analysis.execute()
        analysis.save_csv_result(CSV_RESULT_PATH)
        self.assertTrue(path.isfile(CSV_RESULT_PATH))
        remove(CSV_RESULT_PATH)


if __name__ == '__main__':
    unittest.main()
