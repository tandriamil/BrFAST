#!/usr/bin/python3
"""Test module of the brfast.measures.sensitivity.fp_select_measures module."""

import unittest
from os import path

import pandas as pd
from pandas.testing import assert_frame_equal  # To test DataFrame objects

from brfast.data import MetadataField
from brfast.measures.sensitivity.fpselect import (
    _get_top_k_fingerprints, _preprocess_one_fp_per_browser, PROPORTION_FIELD)

from tests.data import ATTRIBUTES, DummyCleanDataset, DummyFingerprintDataset


class TestGetTopKFingerprints(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset(path.abspath(__file__))
        self._attribute_names = [attribute.name for attribute in ATTRIBUTES]

    def test_top_0_fingerprints(self):
        expected_data = dict(
            [(name, list()) for name in self._attribute_names])
        expected_data[PROPORTION_FIELD] = []  # Added during the computation
        # Empty dataframe with columns only
        expected_dataframe = pd.DataFrame(expected_data)
        # Needed to put the right type
        expected_dataframe = expected_dataframe.astype(dtype={
            ATTRIBUTES[0].name: 'object', ATTRIBUTES[1].name: 'int64',
            ATTRIBUTES[2].name: 'int'
        })
        resulting_dataframe = _get_top_k_fingerprints(self._dataset.dataframe,
                                                      self._attribute_names, 0)
        assert_frame_equal(resulting_dataframe, expected_dataframe)

    def test_top_1_fingerprint(self):
        # Rows seem to be sorted : (Chrome, 100, 1) is then first...
        expected_data = {ATTRIBUTES[0].name: ['Chrome'],
                         ATTRIBUTES[1].name: [100],
                         ATTRIBUTES[2].name: [1],
                         PROPORTION_FIELD: [1/5]}
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(self._dataset.dataframe,
                                                      self._attribute_names, 1)
        assert_frame_equal(resulting_dataframe, expected_dataframe)

    def test_top_3_fingerprints_non_uniques(self):
        # Rows seem to be sorted : (Chrome, 1) is then before (Edge, 1)
        attribute_names = [attribute.name for attribute in ATTRIBUTES]
        attribute_names.remove(ATTRIBUTES[1].name)
        expected_data = {
            ATTRIBUTES[0].name: ['Chrome', 'Edge', 'Firefox'],
            ATTRIBUTES[2].name: [1, 1, 1],
            PROPORTION_FIELD: [2/5, 2/5, 1/5]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(self._dataset.dataframe,
                                                      attribute_names, 3)
        assert_frame_equal(resulting_dataframe, expected_dataframe)

    def test_top_42_fingerprints_non_uniques(self):
        # Rows seem to be sorted : (Chrome, 1) is then before (Edge, 1)
        attribute_names = [attribute.name for attribute in ATTRIBUTES]
        attribute_names.remove(ATTRIBUTES[1].name)
        expected_data = {
            ATTRIBUTES[0].name: ['Chrome', 'Edge', 'Firefox'],
            ATTRIBUTES[2].name: [1, 1, 1],
            PROPORTION_FIELD: [2/5, 2/5, 1/5]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(self._dataset.dataframe,
                                                      attribute_names, 42)
        assert_frame_equal(resulting_dataframe, expected_dataframe)


class TestPreprocessOneFpPerBrowser(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyFingerprintDataset(path.abspath(__file__))

    def test_last_fingerprint_equivalent_to_descending(self):
        expected_data = {
            MetadataField.BROWSER_ID: [1, 2, 3],
            MetadataField.TIME_OF_COLLECT: [
                pd.to_datetime('2021-03-12 00:00:00'),
                pd.to_datetime('2021-03-12 03:00:00'),
                pd.to_datetime('2021-03-12 04:00:00')],
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90],
            ATTRIBUTES[2].name: [1, 1, 1]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        expected_dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)
        resulting_dataframe = _preprocess_one_fp_per_browser(
            self._dataset.dataframe)
        assert_frame_equal(resulting_dataframe, expected_dataframe)

    def test_first_fingerprint_equivalent_to_ascending(self):
        expected_data = {
            MetadataField.BROWSER_ID: [1, 2, 3],
            MetadataField.TIME_OF_COLLECT: [
                pd.to_datetime('2021-03-12 00:00:00'),
                pd.to_datetime('2021-03-12 01:00:00'),
                pd.to_datetime('2021-03-12 02:00:00')],
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90],
            ATTRIBUTES[2].name: [1, 1, 1]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        expected_dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)
        resulting_dataframe = _preprocess_one_fp_per_browser(
            self._dataset.dataframe, last_fingerprint=False)
        assert_frame_equal(resulting_dataframe, expected_dataframe)

    def test_empty_dataset(self):
        data = {
            MetadataField.BROWSER_ID: [],
            MetadataField.TIME_OF_COLLECT: []
        }
        dataframe = pd.DataFrame(data)
        dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)
        ascending_result_dataframe = _preprocess_one_fp_per_browser(
            dataframe, last_fingerprint=False)
        descending_result_dataframe = _preprocess_one_fp_per_browser(dataframe)
        assert_frame_equal(ascending_result_dataframe, dataframe)
        assert_frame_equal(descending_result_dataframe, dataframe)

    def test_dataset_already_clean(self):
        clean_dataset = DummyCleanDataset(path.abspath(__file__))
        ascending_result_dataframe = _preprocess_one_fp_per_browser(
            clean_dataset.dataframe, last_fingerprint=False)
        descending_result_dataframe = _preprocess_one_fp_per_browser(
            clean_dataset.dataframe)
        assert_frame_equal(ascending_result_dataframe, clean_dataset.dataframe)
        assert_frame_equal(descending_result_dataframe,
                           clean_dataset.dataframe)


if __name__ == '__main__':
    unittest.main()
