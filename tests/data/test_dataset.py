#!/usr/bin/python3
"""Test module of the data module of BrFAST."""

import importlib
import unittest
from os import path
from pathlib import PurePath
from typing import List

from pandas.testing import assert_frame_equal  # To test DataFrame objects

from brfast.data.attribute import AttributeSet
from brfast.data.dataset import (
    FingerprintDataset, FingerprintDatasetFromFile,
    FingerprintDatasetFromCSVFile, FingerprintDatasetFromCSVInMemory,
    MetadataField, MissingMetadatasFields)

from tests.data import (
    ATTRIBUTES, data_subset,
    # FingerprintDataset dummy implementations
    DummyCleanDataset, DummyEmptyDataset, DummyFingerprintDataset,
    DummyFingerprintDatasetMissingSetCandidateAttributes,
    DummyFingerprintDatasetMissingProcessDataset,
    DummyDatasetMissingBrowserId, DummyDatasetMissingTimeOfCollect,
    # FingerprintDatasetFromFile dummy implementations
    DummyFPCleanDatasetDatasetFromFile, DummyFPDatasetFromFile,
    DummyFPEmptyDatasetFromFile,
    DummyFPDatasetFromFileMissingProcessDataset)

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
pd = importlib.import_module(params['DataAnalysis']['engine'])

RELATIVE_PATH_TO_DATASETS = 'assets/fingerprint-datasets'
UNEXISTENT_PATH = '/this/path/does/not/exist'
DATASET_PATHS = {
    'empty': 'fingerprint-sample-empty.csv',
    'sample': 'fingerprint-sample.csv',
    'clean': 'fingerprint-sample-clean.csv',
    'missing_browser_id': 'fingerprint-sample-missing-browser-id.csv',
    'missing_time_of_collect': 'fingerprint-sample-missing-time-of-collect.csv'
}
DATASET_DATA = {
    'empty': {MetadataField.BROWSER_ID: [], MetadataField.TIME_OF_COLLECT: []},
    'sample': {
        MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
        MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-04-29 17:00:00'),
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    },
    'clean': {
        MetadataField.BROWSER_ID: [1, 2, 3, 4, 5],
        MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-04-29 17:00:00'),
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 100, 80],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    }
}


class TestFingerprintDataset(unittest.TestCase):

    def setUp(self):
        self._dummy_fp_dataset = DummyFingerprintDataset()
        self._empty_dataset = DummyEmptyDataset()
        self._clean_dataset = DummyCleanDataset()

    def test_interface_error(self):
        with self.assertRaises(NotImplementedError):
            fp_dataset_interface = FingerprintDataset()

    def test_missing_process_dataset(self):
        with self.assertRaises(NotImplementedError):
            fp_dataset_missing_process_dataset = (
                DummyFingerprintDatasetMissingProcessDataset())

    def test_missing_set_candidate_attributes(self):
        with self.assertRaises(NotImplementedError):
            fp_dataset_missing_set_candidate_attributes = (
                DummyFingerprintDatasetMissingSetCandidateAttributes())

    def test_missing_browser_id_field(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_browser_id = DummyDatasetMissingBrowserId()

    def test_missing_time_of_collect(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_toc = DummyDatasetMissingTimeOfCollect()

    def test_repr(self):
        self.assertIsInstance(repr(self._dummy_fp_dataset), str)
        self.assertIsInstance(repr(self._empty_dataset), str)
        self.assertIsInstance(repr(self._clean_dataset), str)

    def check_dataframe_property(self, dataset: FingerprintDataset,
                                 expected_data: dict):
        self.assertIsInstance(dataset.dataframe, pd.DataFrame)
        self.assertEqual(len(dataset.dataframe),
                         len(expected_data[MetadataField.BROWSER_ID]))
        comparison_dataframe = pd.DataFrame(expected_data)

        # Format and set the indices
        comparison_dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            comparison_dataframe[MetadataField.TIME_OF_COLLECT])
        browser_id_type = dataset.dataframe.index.get_level_values(0).dtype
        comparison_dataframe[MetadataField.BROWSER_ID] = (
            comparison_dataframe[MetadataField.BROWSER_ID]
            .astype(browser_id_type))
        comparison_dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)

        assert_frame_equal(dataset.dataframe, comparison_dataframe,
                           check_frame_type=False)  # As modin can be used
        with self.assertRaises(AttributeError):
            dataset.dataframe = pd.DataFrame()

    def test_dataframe_property(self):
        self.check_dataframe_property(self._dummy_fp_dataset,
                                      self._dummy_fp_dataset.DATAS)
        self.check_dataframe_property(self._empty_dataset,
                                      self._empty_dataset.DATAS)
        self.check_dataframe_property(self._clean_dataset,
                                      self._clean_dataset.DATAS)

    def check_candidate_attributes_property(self, dataset: FingerprintDataset,
                                            attribute_set: AttributeSet):
        self.assertEqual(dataset.candidate_attributes, attribute_set)
        with self.assertRaises(AttributeError):
            self._empty_dataset.candidate_attributes = AttributeSet()

    def test_candidate_attributes_property(self):
        self.check_candidate_attributes_property(self._dummy_fp_dataset,
                                                 AttributeSet(ATTRIBUTES))
        self.check_candidate_attributes_property(self._empty_dataset,
                                                 AttributeSet())
        self.check_candidate_attributes_property(self._clean_dataset,
                                                 AttributeSet(ATTRIBUTES))

    def check_one_fp_per_browser(self, dataset: FingerprintDataset,
                                 expected_data: dict, expected_rows: List[int],
                                 last_fingerprint: bool):
        expected_data = data_subset(expected_rows, expected_data)
        expected_dataframe = pd.DataFrame(expected_data)

        # Format and set the indices
        expected_dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            expected_dataframe[MetadataField.TIME_OF_COLLECT])
        browser_id_type = dataset.dataframe.index.get_level_values(0).dtype
        expected_dataframe[MetadataField.BROWSER_ID] = (
            expected_dataframe[MetadataField.BROWSER_ID]
            .astype(browser_id_type))
        expected_dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)

        df_w_1_fp_p_bswr = dataset.get_df_w_one_fp_per_browser(
            last_fingerprint=last_fingerprint)
        self.assertIsInstance(df_w_1_fp_p_bswr, pd.DataFrame)
        self.assertEqual(len(df_w_1_fp_p_bswr), len(expected_dataframe))
        assert_frame_equal(df_w_1_fp_p_bswr, expected_dataframe,
                           check_frame_type=False)  # As modin can be used
        # Just to check that the caching works fine we call this two times
        assert_frame_equal(dataset.get_df_w_one_fp_per_browser(
            last_fingerprint=last_fingerprint), expected_dataframe,
                           check_frame_type=False)  # As modin can be used

    def test_get_df_w_one_fp_per_browser_first_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      self._dummy_fp_dataset.DATAS,
                                      [0, 1, 2], False)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      self._empty_dataset.DATAS, [], False)
        clean_dataset_len = len(
            self._clean_dataset.DATAS[MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      self._clean_dataset.DATAS,
                                      list(range(clean_dataset_len)), False)

    def test_get_df_w_one_fp_per_browser_last_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      self._dummy_fp_dataset.DATAS,
                                      [0, 3, 4], True)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      self._empty_dataset.DATAS, [], True)
        clean_dataset_len = len(
            self._clean_dataset.DATAS[MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      self._clean_dataset.DATAS,
                                      list(range(clean_dataset_len)), True)


class TestFingerprintDatasetFromFile(TestFingerprintDataset):

    def setUp(self):
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        fingerprint_dataset_path = tests_module_path.joinpath(
            RELATIVE_PATH_TO_DATASETS)

        self._sample_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['sample'])
        self._dummy_fp_dataset = DummyFPDatasetFromFile(self._sample_path)
        self._empty_dataset = DummyFPEmptyDatasetFromFile(self._sample_path)
        self._clean_dataset = DummyFPCleanDatasetDatasetFromFile(
            self._sample_path)

    def test_interface_error(self):
        with self.assertRaises(NotImplementedError):
            fp_dataset_interface = FingerprintDatasetFromFile(
                self._sample_path)

    def test_missing_process_dataset(self):
        with self.assertRaises(NotImplementedError):
            fp_dataset_missing_process_dataset = (
                DummyFPDatasetFromFileMissingProcessDataset(self._sample_path))

    def test_missing_set_candidate_attributes(self):
        pass  # This function is defined in this interface

    def test_unexistent_path(self):
        with self.assertRaises(FileNotFoundError):
            erroneous_dataset = FingerprintDatasetFromFile(UNEXISTENT_PATH)

    def test_dataset_path_property(self):
        self.assertEqual(self._dummy_fp_dataset.dataset_path,
                         self._sample_path)
        self.assertEqual(self._empty_dataset.dataset_path, self._sample_path)
        self.assertEqual(self._clean_dataset.dataset_path, self._sample_path)
        with self.assertRaises(AttributeError):
            self._dummy_fp_dataset.dataset_path = UNEXISTENT_PATH
        with self.assertRaises(AttributeError):
            self._empty_dataset.dataset_path = UNEXISTENT_PATH
        with self.assertRaises(AttributeError):
            self._clean_dataset.dataset_path = UNEXISTENT_PATH

    # The other tests are taken directly from TestFingerprintDataset


class TestFingerprintDatasetFromCSVFile(TestFingerprintDatasetFromFile):

    def setUp(self):
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        fingerprint_dataset_path = tests_module_path.joinpath(
            RELATIVE_PATH_TO_DATASETS)

        self._sample_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['sample'])
        self._empty_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['empty'])
        self._clean_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['clean'])
        self._missing_browser_id_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['missing_browser_id'])
        self._missing_time_of_collect_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['missing_time_of_collect'])

        self._dummy_fp_dataset = FingerprintDatasetFromCSVFile(
            self._sample_path)
        self._empty_dataset = FingerprintDatasetFromCSVFile(
            self._empty_path)
        self._clean_dataset = FingerprintDatasetFromCSVFile(
            self._clean_path)

    def test_interface_error(self):
        pass  # Not an interface anymore

    def test_missing_process_dataset(self):
        pass  # This function is defined in this interface

    def test_missing_browser_id_field(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_browser_id = FingerprintDatasetFromCSVFile(
                self._missing_browser_id_path)

    def test_missing_time_of_collect(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_toc = FingerprintDatasetFromCSVFile(
                self._missing_time_of_collect_path)

    def test_unexistent_path(self):
        with self.assertRaises(FileNotFoundError):
            erroneous_dataset = FingerprintDatasetFromCSVFile(UNEXISTENT_PATH)

    def test_dataset_path_property(self):
        self.assertEqual(self._dummy_fp_dataset.dataset_path,
                         self._sample_path)
        self.assertEqual(self._empty_dataset.dataset_path, self._empty_path)
        self.assertEqual(self._clean_dataset.dataset_path, self._clean_path)
        with self.assertRaises(AttributeError):
            self._dummy_fp_dataset.dataset_path = UNEXISTENT_PATH
        with self.assertRaises(AttributeError):
            self._empty_dataset.dataset_path = UNEXISTENT_PATH
        with self.assertRaises(AttributeError):
            self._clean_dataset.dataset_path = UNEXISTENT_PATH

    def test_dataframe_property(self):
        self.check_dataframe_property(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'])
        self.check_dataframe_property(self._empty_dataset,
                                      DATASET_DATA['empty'])
        self.check_dataframe_property(self._clean_dataset,
                                      DATASET_DATA['clean'])

    def test_get_df_w_one_fp_per_browser_first_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'], [0, 1, 2], False)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      DATASET_DATA['empty'], [], False)
        clean_dataset_len = len(
            DATASET_DATA['clean'][MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      DATASET_DATA['clean'],
                                      list(range(clean_dataset_len)), False)

    def test_get_df_w_one_fp_per_browser_last_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'], [0, 3, 4], True)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      DATASET_DATA['empty'], [], True)
        clean_dataset_len = len(
            DATASET_DATA['clean'][MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      DATASET_DATA['clean'],
                                      list(range(clean_dataset_len)), True)


class TestFingerprintDatasetFromCSVInMemory(TestFingerprintDataset):

    def setUp(self):
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        fingerprint_dataset_path = tests_module_path.joinpath(
            RELATIVE_PATH_TO_DATASETS)

        self._sample_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['sample'])
        self._empty_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['empty'])
        self._clean_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['clean'])
        self._missing_browser_id_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['missing_browser_id'])
        self._missing_time_of_collect_path = fingerprint_dataset_path.joinpath(
            DATASET_PATHS['missing_time_of_collect'])

        self._sample_file = open(self._sample_path, 'r')
        self._empty_file = open(self._empty_path, 'r')
        self._clean_file = open(self._clean_path, 'r')
        self._missing_browser_id_file = open(self._missing_browser_id_path,
                                             'r')
        self._missing_time_of_collect_file = open(
            self._missing_time_of_collect_path, 'r')

        self._dummy_fp_dataset = FingerprintDatasetFromCSVInMemory(
            self._sample_file)
        self._empty_dataset = FingerprintDatasetFromCSVInMemory(
            self._empty_file)
        self._clean_dataset = FingerprintDatasetFromCSVInMemory(
            self._clean_file)

    def tearDown(self):
        self._sample_file.close()
        self._empty_file.close()
        self._clean_file.close()
        self._missing_browser_id_file.close()
        self._missing_time_of_collect_file.close()

    def test_interface_error(self):
        pass  # Not an interface anymore

    def test_missing_process_dataset(self):
        pass  # This function is defined in this interface

    def test_missing_set_candidate_attributes(self):
        pass  # This function is defined in this interface

    def test_missing_browser_id_field(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_browser_id = FingerprintDatasetFromCSVInMemory(
                self._missing_browser_id_file)

    def test_missing_time_of_collect(self):
        with self.assertRaises(MissingMetadatasFields):
            fp_dataset_missing_toc = FingerprintDatasetFromCSVInMemory(
                self._missing_time_of_collect_file)

    def test_dataframe_property(self):
        self.check_dataframe_property(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'])
        self.check_dataframe_property(self._empty_dataset,
                                      DATASET_DATA['empty'])
        self.check_dataframe_property(self._clean_dataset,
                                      DATASET_DATA['clean'])

    def test_get_df_w_one_fp_per_browser_first_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'], [0, 1, 2], False)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      DATASET_DATA['empty'], [], False)
        clean_dataset_len = len(
            DATASET_DATA['clean'][MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      DATASET_DATA['clean'],
                                      list(range(clean_dataset_len)), False)

    def test_get_df_w_one_fp_per_browser_last_fingerprint(self):
        self.check_one_fp_per_browser(self._dummy_fp_dataset,
                                      DATASET_DATA['sample'], [0, 3, 4], True)
        self.check_one_fp_per_browser(self._empty_dataset,
                                      DATASET_DATA['empty'], [], True)
        clean_dataset_len = len(
            DATASET_DATA['clean'][MetadataField.BROWSER_ID])
        self.check_one_fp_per_browser(self._clean_dataset,
                                      DATASET_DATA['clean'],
                                      list(range(clean_dataset_len)), True)


if __name__ == '__main__':
    unittest.main()
