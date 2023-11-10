#!/usr/bin/python3
"""Module containing the implementation of data-related objects for tests."""

import importlib
import operator
from typing import List

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import (
    FingerprintDataset, FingerprintDatasetFromFile, MetadataField)

pd = importlib.import_module(params['DataAnalysis']['engine'])

ATTRIBUTES = [Attribute(1, 'user_agent'), Attribute(2, 'timezone'),
              Attribute(3, 'do_not_track')]
NON_EXISTENT_ATTRIBUTE = Attribute(42, 'missing_from_dataset')


# ==================== FingerprintDataset Implementations =====================
class DummyFingerprintDataset(FingerprintDataset):
    """Dummy fingerprint class to define the required functions."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
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


class DummyDatasetMissingBrowserId(DummyFingerprintDataset):
    """A dummy fingerprint dataset with the browser_id metadata missing."""

    DATAS = {
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90]
    }

    def _process_dataset(self):
        self._dataframe = pd.DataFrame(self.DATAS)

        # Format and set the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])
        self._dataframe.set_index([MetadataField.TIME_OF_COLLECT],
                                  inplace=True)


class DummyDatasetMissingTimeOfCollect(DummyFingerprintDataset):
    """A dummy fingerprint dataset with time_of_collect metadata missing."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90]
    }

    def _process_dataset(self):
        self._dataframe = pd.DataFrame(self.DATAS)

        # Set the indices
        self._dataframe.set_index([MetadataField.BROWSER_ID], inplace=True)


class DummyCleanDataset(DummyFingerprintDataset):
    """A dummy clean dataset with a single fingerprint per browser."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 4, 5],
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 100, 80],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    }


class DummyEmptyDataset(DummyFingerprintDataset):
    """A dummy fingerprint dataset that has an empty dataframe."""

    DATAS = {MetadataField.BROWSER_ID: [], MetadataField.TIME_OF_COLLECT: []}

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet()


class DummyFingerprintDatasetMissingSetCandidateAttributes(FingerprintDataset):
    """Dummy FingerprintDataset that misses _set_candidate_attributes()."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    }

    def _process_dataset(self):
        self._dataframe = pd.DataFrame(self.DATAS)

        # Format and set the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class DummyFingerprintDatasetMissingProcessDataset(FingerprintDataset):
    """Dummy FingerprintDataset class that misses _process_dataset()."""

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet(ATTRIBUTES)
# ================= End of FingerprintDataset Implementations =================


# ================ FingerprintDatasetFromFile Implementations =================
class DummyFPDatasetFromFile(FingerprintDatasetFromFile):
    """Dummy FingerprintDatasetFromFile class."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 120, 90],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    }

    def _process_dataset(self):
        self._dataframe = pd.DataFrame(self.DATAS)

        # Format and set the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class DummyFPCleanDatasetDatasetFromFile(DummyFPDatasetFromFile):
    """A dummy clean dataset with a single fingerprint per browser."""

    DATAS = {
        MetadataField.BROWSER_ID: [1, 2, 3, 4, 5],
        MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                     periods=5, freq='H'),
        ATTRIBUTES[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                             'Edge'],
        ATTRIBUTES[1].name: [60, 120, 90, 100, 80],
        ATTRIBUTES[2].name: [1, 1, 1, 1, 1]
    }


class DummyFPEmptyDatasetFromFile(DummyFPDatasetFromFile):
    """A dummy fingerprint dataset that has an empty dataframe."""

    DATAS = {MetadataField.BROWSER_ID: [], MetadataField.TIME_OF_COLLECT: []}


class DummyFPDatasetFromFileMissingProcessDataset(FingerprintDatasetFromFile):
    """Dummy fingerprint class that misses _process_dataset()."""

    def _set_candidate_attributes(self):
        self._candidate_attributes = AttributeSet(ATTRIBUTES)
# ============= End of FingerprintDatasetFromFile Implementations =============


# ============================ Utility Functions ==============================
def data_subset(rows_to_hold: List[int], data: dict) -> dict:
    """Obtain a subset of the datas as a dictionary given the rows.

    Args:
        rows_to_hold: The id of the rows to hold from the input data.
        data: The data from which we take a sample.

    Returns:
        A dictionary with the data only composed of the given rows.
    """
    result_data = {}
    if rows_to_hold:
        for column, rows_values in data.items():
            result_data[column] = (
                operator.itemgetter(*rows_to_hold)(rows_values))
    else:
        for column in data:
            result_data[column] = []
    return result_data
# ========================= End of Utility Functions ==========================
