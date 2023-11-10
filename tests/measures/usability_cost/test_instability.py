#!/usr/bin/python3
"""Tests of the brfast.measures.usability_cost.memory module."""

import importlib
import unittest
from os import path, remove

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset, MetadataField
from brfast.measures.usability_cost.instability import (
    _compute_attributes_instability, ProportionOfChanges)
from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        DummyFingerprintDataset, NON_EXISTENT_ATTRIBUTE)

pd = importlib.import_module(params['DataAnalysis']['engine'])

CSV_RESULT_PATH = 'test_instability.csv'


class TestComputeAttributesInstability(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attributes = AttributeSet(ATTRIBUTES)

    def _get_grouped_by_browser(self):
        # 1. Group by the browser id (no sort for performances, no group key to
        #    not add a column with the group key)
        # 2. Sort by the time of collection for each group (give a DataFrame)
        # 3. Regroup by the browser id, here each group has the fingerprints
        #    sorted by the time of collection
        return (self._dataset.dataframe
                .groupby(MetadataField.BROWSER_ID, sort=False,
                         group_keys=False)
                .apply(lambda group_df: group_df.sort_values(
                    MetadataField.TIME_OF_COLLECT))
                .groupby(MetadataField.BROWSER_ID, sort=False,
                         group_keys=False))

    def test_empty_dataset(self):
        self._dataset = DummyEmptyDataset()
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {ATTRIBUTES[0]: 0.0, ATTRIBUTES[1]: 0.0,
                           ATTRIBUTES[2]: 0.0}
        self.assertDictEqual(expected_result, attributes_instability)

    def test_non_existent_attribute(self):
        self._attributes.add(NON_EXISTENT_ATTRIBUTE)
        grouped_by_browser = self._get_grouped_by_browser()
        with self.assertRaises(KeyError):
            _compute_attributes_instability(grouped_by_browser,
                                            self._attributes)

    def test_empty_attributes(self):
        self._attributes = AttributeSet({})
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {}
        self.assertDictEqual(expected_result, attributes_instability)

    def test_empty_dataset_and_attributes(self):
        self._dataset = DummyEmptyDataset()
        self._attributes = AttributeSet({})
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {}
        self.assertDictEqual(expected_result, attributes_instability)

    def test_clean_dataset(self):
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {ATTRIBUTES[0]: 0.0, ATTRIBUTES[1]: 0.0,
                           ATTRIBUTES[2]: 0.0}
        self.assertDictEqual(expected_result, attributes_instability)

    def test_dummy_fingerprint_dataset(self):
        self._dataset = DummyFingerprintDataset()
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {ATTRIBUTES[0]: 0.0, ATTRIBUTES[1]: 0.0,
                           ATTRIBUTES[2]: 0.0}
        self.assertDictEqual(expected_result, attributes_instability)

    def test_dummy_dataset_with_changes(self):
        self._dataset = DummyDatasetWithChanges()
        grouped_by_browser = self._get_grouped_by_browser()
        attributes_instability = _compute_attributes_instability(
            grouped_by_browser, self._attributes)
        expected_result = {ATTRIBUTES[0]: 1/2, ATTRIBUTES[1]: 1.0,
                           ATTRIBUTES[2]: 0.0}
        self.assertDictEqual(expected_result, attributes_instability)


class TestProportionOfChanges(unittest.TestCase):

    def test_empty_dataset(self):
        empty_dataset = DummyEmptyDataset()
        expected_result = {}
        analysis = ProportionOfChanges(empty_dataset)
        analysis.execute()
        self.assertDictEqual(expected_result, analysis.result)

    def test_clean_dataset(self):
        clean_dataset = DummyCleanDataset()
        expected_result = {ATTRIBUTES[0]: 0.0, ATTRIBUTES[1]: 0.0,
                           ATTRIBUTES[2]: 0.0}
        analysis = ProportionOfChanges(clean_dataset)
        analysis.execute()
        self.assertDictEqual(expected_result, analysis.result)

    def test_dummy_fingerprint_dataset(self):
        dataset = DummyFingerprintDataset()
        expected_result = {ATTRIBUTES[0]: 0.0, ATTRIBUTES[1]: 0.0,
                           ATTRIBUTES[2]: 0.0}
        analysis = ProportionOfChanges(dataset)
        analysis.execute()
        self.assertDictEqual(expected_result, analysis.result)

    def test_dummy_dataset_with_changes(self):
        dataset_with_changes = DummyDatasetWithChanges()
        expected_result = {ATTRIBUTES[0]: 1/2, ATTRIBUTES[1]: 1.0,
                           ATTRIBUTES[2]: 0.0}
        analysis = ProportionOfChanges(dataset_with_changes)
        analysis.execute()
        self.assertDictEqual(expected_result, analysis.result)

    def test_save_csv_result(self):
        clean_dataset = DummyCleanDataset()
        analysis = ProportionOfChanges(clean_dataset)
        analysis.execute()
        analysis.save_csv_result(CSV_RESULT_PATH)
        self.assertTrue(path.isfile(CSV_RESULT_PATH))
        remove(CSV_RESULT_PATH)


class DummyDatasetWithChanges(FingerprintDataset):
    """Dummy fingerprint class to define the required functions."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 1, 1, 2, 2, 2, 3, 3, 3],
        MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-05-03'),
                                                     periods=9, freq='H'),
        # First attribute: Changing half of the consecutive fingerprints
        #     1st browser: 1 change over the 2 consecutive fingerprints
        #     2nd browser: 2 changes over the 2 consecutive fingerprints
        #     3rd browser: 0 changes over the 2 consecutive fingerprints
        ATTRIBUTES[0].name: ['Firefox', 'Firefox', 'FirefoxChange',
                             'Chrome', 'ChromeChange', 'Chrome',
                             'Edge', 'Edge', 'Edge'],
        # Second attribute: Changing everytime
        ATTRIBUTES[1].name: [10, 20, 30, 90, 100, 110, 50, 60, 70],
        # Third attribute: no change at all for each browser
        ATTRIBUTES[2].name: [1, 1, 1, 2, 2, 2, 3, 3, 3]
    }

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet(ATTRIBUTES)

    def _process_dataset(self):
        self._dataframe = pd.DataFrame(self.DATAS)

        # Format and set the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


if __name__ == '__main__':
    unittest.main()
