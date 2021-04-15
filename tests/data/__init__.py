#!/usr/bin/python3
"""Module containing the implementation of data-related objects for tests."""

import importlib

from brfast.data import (Attribute, AttributeSet, FingerprintDataset,
                         MetadataField)

# Import the engine of the analysis module (pandas or modin)
from brfast import config
pd = importlib.import_module(config['DataAnalysis']['engine'])

ATTRIBUTES = [Attribute(1, 'user_agent'), Attribute(2, 'timezone'),
              Attribute(3, 'do_not_track')]


class DummyFingerprintDataset(FingerprintDataset):
    """Dummy fingerprint class to define the required functions."""

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet(ATTRIBUTES)

    def _process_dataset(self):
        self._datas = {
            MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
            MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-03-12'),
                                                         periods=5, freq='H'),
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                                 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90, 120, 90],
            ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
        }
        self._dataframe = pd.DataFrame(self._datas)
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class DummyDatasetMissingBrowserId(DummyFingerprintDataset):
    """A dummy fingerprint dataset with the browser_id metadata missing."""

    def _process_dataset(self):
        self._datas = {
            MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-03-12'),
                                                         periods=5, freq='H'),
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                                 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90, 120, 90]
        }
        self._dataframe = pd.DataFrame(self._datas)
        self._dataframe.set_index([MetadataField.TIME_OF_COLLECT],
                                  inplace=True)


class DummyDatasetMissingTimeOfCollect(DummyFingerprintDataset):
    """A dummy fingerprint dataset with time_of_collect metadata missing."""

    def _process_dataset(self):
        self._datas = {
            MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                                 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90, 120, 90]
        }
        self._dataframe = pd.DataFrame(self._datas)
        self._dataframe.set_index([MetadataField.BROWSER_ID], inplace=True)


class DummyCleanDataset(FingerprintDataset):
    """A dummy clean dataset with a single fingerprint per browser."""

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet(ATTRIBUTES)

    def _process_dataset(self):
        self._datas = {
            MetadataField.BROWSER_ID: [1, 2, 3, 4, 5],
            MetadataField.TIME_OF_COLLECT: pd.date_range(('2021-03-12'),
                                                         periods=5, freq='H'),
            ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                                 'Edge'],
            ATTRIBUTES[1].name: [60, 120, 90, 100, 80],
            ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
        }
        self._dataframe = pd.DataFrame(self._datas)
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class DummyEmptyDataset(FingerprintDataset):
    """A dummy fingerprint dataset that has an empty dataframe."""

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet()

    def _process_dataset(self):
        self._dataframe = pd.DataFrame({MetadataField.BROWSER_ID: [],
                                        MetadataField.TIME_OF_COLLECT: []})
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)
