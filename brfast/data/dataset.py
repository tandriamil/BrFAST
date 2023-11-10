#!/usr/bin/python3
"""brfast.data.dataset module: Classes related to the fingerprint datasets."""

import importlib
from os import path
from pathlib import Path
from typing import TextIO

from loguru import logger
from werkzeug.datastructures import FileStorage

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet

pd = importlib.import_module(params.get('DataAnalysis', 'engine'))


# ============================== Utility classes ==============================
class MetadataField:
    """Class representing the required metadata fields."""

    BROWSER_ID = 'browser_id'
    TIME_OF_COLLECT = 'time_of_collect'
    ALL = {BROWSER_ID, TIME_OF_COLLECT}


class MissingMetadataFields(Exception):
    """The required metadata columns are missing from the dataset."""


# ==================== Fingerprint dataset related classes ====================
class FingerprintDataset:
    """A fingerprint dataset (abstract class)."""

    def __init__(self):
        """Initialize."""
        self._dataframe, self._candidate_attributes = None, None

        # The dataframes with a single fingerprint per browser, lazily computed
        self._first_fp_df, self._last_fp_df = None, None

        # Process the dataset
        self._process_dataset()

        # Check that the necessary metadata are present
        required_metadata = MetadataField.ALL
        if not (isinstance(self._dataframe.index, pd.MultiIndex)               # noqa
                and required_metadata.issubset(self._dataframe.index.names)):  # noqa
            raise MissingMetadataFields(
                'The required metadata fields and indices '
                f'{required_metadata} are missing from the dataset.')

        # Set the candidate attributes
        self._set_candidate_attributes()

    def __repr__(self) -> str:
        """Provide a string representation of this fingerprint dataset.

        Returns:
            A string representation of this fingerprint dataset.
        """
        return f'{self.__class__.__name__}'

    def _process_dataset(self):
        """Process the dataset to obtain a DataFrame from the file.

        - The resulting fingerprint dataset is stored in self._dataframe.
        - The fingerprint dataset has to be a DataFrame with the two
          indices being browser_id (int64) and time_of_collect (datetime64).
        - The columns are named after the attributes and have the value
          collected for the browser browser_id at the time time_of_collect.
        - The name of each column should correspond to the attribute.name
          property of an attribute of the candidate attributes.

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        raise NotImplementedError

    def _set_candidate_attributes(self):
        """Set the candidate attributes.

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        raise NotImplementedError

    @property
    def dataframe(self) -> pd.DataFrame:
        """Give the fingerprint dataset as a DataFrame.

        Returns:
            The fingerprint dataset as a DataFrame.
        """
        return self._dataframe

    @property
    def candidate_attributes(self) -> AttributeSet:
        """Give the candidate attributes as an AttributeSet.

        Returns:
            The candidate attributes as an AttributeSet.
        """
        return self._candidate_attributes

    def get_df_w_one_fp_per_browser(self, last_fingerprint: bool = True
                                    ) -> pd.DataFrame:
        """Provide a dataframe with only one fingerprint per browser.

        Args:
            last_fingerprint: Whether we should only hold the last fingerprint
                              of each user, otherwise it is the first
                              fingerprint.

        Returns:
            A dataframe with only one fingerprint per browser, which is the
            first or the last one.
        """
        # Last fingerprint
        if last_fingerprint:

            logger.debug(f'Getting the dataframe {self} with the last '
                         'fingerprint only for each browser')

            if self._last_fp_df is None:
                logger.debug(f'Generate the dataframe {self} with the last'
                             ' fingerprint only for each browser')
                self._last_fp_df = self._preprocess_one_fp_per_browser(
                    last_fingerprint)

                # If the two dataframes have the same length, they are
                # equal (i.e., no duplicates were removed). We just
                # reference the dataframe to save memory.
                if len(self._last_fp_df) == len(self._dataframe):
                    logger.debug('The two dataframes are equal, '
                                 '_last_fp_df is then the input dataframe')
                    self._last_fp_df = self._dataframe

            # Return the resulting DataFrame
            return self._last_fp_df

        # First fingerprint
        logger.debug(f'Getting the dataframe {self} with the first '
                     'fingerprint only for each browser')

        if self._first_fp_df is None:
            logger.debug(f'Generate the dataframe {self} with the first '
                         'fingerprint only for each browser')
            self._first_fp_df = self._preprocess_one_fp_per_browser(
                last_fingerprint)

            # If the two dataframes have the same length, they are
            # equal (i.e., no duplicates were removed). We just
            # reference the dataframe to save memory.
            if len(self._first_fp_df) == len(self._dataframe):
                logger.debug('The two dataframes are equal, '
                             '_first_fp_df is then the input dataframe')
                self._first_fp_df = self._dataframe

        # Return the resulting DataFrame
        return self._first_fp_df

    def _preprocess_one_fp_per_browser(self, last_fingerprint: bool = True
                                       ) -> pd.DataFrame:
        """Preprocess this fingerprint dataset to hold a single fp per browser.

        Args:
            last_fingerprint: Whether we should only hold the last fingerprint
                              of each user, otherwise it is the first
                              fingerprint.

        Returns:
            A dataframe with only one fingerprint per browser, which is the
            first or the last one.
        """
        which_fp_to_hold = 'last' if last_fingerprint else 'first'
        logger.debug('Preprocessing the dataset to hold a single fingerprint '
                     f'per browser, taking the {which_fp_to_hold} '
                     'fingerprint.')

        # If the dataframe is empty, just return it
        if self._dataframe.empty:
            logger.debug('The given dataframe is empty, returning the '
                         'dataframe without modifying it.')
            return self._dataframe

        # 1. We group the fingerprints (=rows) by the browser id. As we do not
        #    care about the order of the browser ids, we turn the sorting off
        #    for better performances. We need to disable the group keys to not
        #    have an additional index with the value of the index 'browser_id'.
        grouped_by_browser = self._dataframe.groupby(
            MetadataField.BROWSER_ID, sort=False, group_keys=False)

        # 2. For each group (= a browser id), we sort the fingerprints by the
        #    time they were collected at. If we want the last fingerprint, then
        #    we sort them in descending manner (= not ascending) to have the
        #    latest first.
        # 3. We only hold a fingerprint for each group, hence for each browser.
        return grouped_by_browser.apply(
            lambda row: row.sort_values(MetadataField.TIME_OF_COLLECT,
                                        ascending=not last_fingerprint)
                           .head(1))


class FingerprintDatasetFromFile(FingerprintDataset):
    """A fingerprint dataset read from a file."""

    def __init__(self, dataset_path: Path):
        """Initialize the FingerprintDataset with the path to the dataset.

        Args:
            dataset_path: The path to the fingerprint dataset.

        Raises:
            FileNotFoundError: There is no file at the given dataset path.
        """
        if not path.isfile(dataset_path):
            raise FileNotFoundError(f'The dataset file at {dataset_path} is '
                                    'not found.')
        self._dataset_path = dataset_path
        super().__init__()

    def __repr__(self) -> str:
        """Provide a string representation of this fingerprint dataset.

        Returns:
            A string representation of this fingerprint dataset.
        """
        return f'{self.__class__.__name__}({self._dataset_path})'

    def _process_dataset(self):
        """Process the dataset to obtain a DataFrame from the file.

        - The resulting fingerprint dataset is stored in self._dataframe.
        - The fingerprint dataset has to be a DataFrame with the two
          indices being browser_id (int64) and time_of_collect (datetime64).
        - The columns are named after the attributes and have the value
          collected for the browser browser_id at the time time_of_collect.
        - The name of each column should correspond to the attribute.name
          property of an attribute of the candidate attributes.

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        raise NotImplementedError

    def _set_candidate_attributes(self):
        """Set the candidate attributes.

        This implementation generates the candidate attributes from the columns
        of the DataFrame, ignoring the browser_id and time_of_collect fields.
        """
        self._candidate_attributes = AttributeSet()
        for column_id, column in enumerate(self._dataframe.columns, 1):
            attribute = Attribute(column_id, column)
            self._candidate_attributes.add(attribute)

    @property
    def dataset_path(self) -> Path:
        """Give the path to the fingerprint dataset.

        Returns:
            The path to the fingerprint dataset.
        """
        return self._dataset_path


class FingerprintDatasetFromCSVFile(FingerprintDatasetFromFile):
    """A fingerprint dataset read from a csv file."""

    def _process_dataset(self):
        """Process the dataset to obtain a DataFrame from the file.

        - The resulting fingerprint dataset is stored in self._dataframe.
        - The fingerprint dataset has to be a DataFrame with the two
          indices being browser_id (int64) and time_of_collect (datetime64).
        - The columns are named after the attributes and have the value
          collected for the browser browser_id at the time time_of_collect.
        - The name of each column should correspond to the attribute.name
          property of an attribute of the candidate attributes.

        This implementation generates a DataFrame from the csv stored at
        self._dataset_path with the two indices set.
        """
        # Read the file from a csv
        # + Parse the 'time_of_collect' column as a date with the option
        #   infer_datetime_format activated for performances
        self._dataframe = pd.read_csv(self._dataset_path, index_col=False)

        # Check that the necessary metadata are present
        for required_metadata in MetadataField.ALL:
            if required_metadata not in self._dataframe:
                raise MissingMetadataFields(
                    f'The required metadata field {required_metadata} is '
                    'missing from the dataset.')

        # Format the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])

        # Set the indices as 'browser_id' and 'time_of_collect'
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class FingerprintDatasetFromCSVInMemory(FingerprintDataset):
    """A fingerprint dataset read from an in memory csv file."""

    def __init__(self, file_handle: FileStorage | TextIO):
        """Initialize with the file handle of the in memory csv file.

        Args:
            file_handle: The file handle of the in memory csv file.
        """
        self._file_handle = file_handle
        super().__init__()

    def _process_dataset(self):
        """Process the dataset to obtain a DataFrame from the file.

        - The resulting fingerprint dataset is stored in self._dataframe.
        - The fingerprint dataset has to be a DataFrame with the two
          indices being browser_id (int64) and time_of_collect (datetime64).
        - The columns are named after the attributes and have the value
          collected for the browser browser_id at the time time_of_collect.
        - The name of each column should correspond to the attribute.name
          property of an attribute of the candidate attributes.

        This implementation generates a DataFrame from the csv stored in memory
        with the two indices set.
        """
        # Read the file from the in memory csv file
        # + Parse the 'time_of_collect' column as a date with the option
        #   infer_datetime_format activated for performances
        self._dataframe = pd.read_csv(self._file_handle, index_col=False)

        # Check that the necessary metadata are present
        for required_metadata in MetadataField.ALL:
            if required_metadata not in self._dataframe:
                raise MissingMetadataFields(
                    f'The required metadata field {required_metadata} is '
                    'missing from the dataset.')

        # Format the indices
        self._dataframe[MetadataField.TIME_OF_COLLECT] = pd.to_datetime(
            self._dataframe[MetadataField.TIME_OF_COLLECT])

        # Set the indices as 'browser_id' and 'time_of_collect'
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)

        # Remove the file handle as it is not needed anymore and cannot be
        # pickled
        del self._file_handle

    def _set_candidate_attributes(self):
        """Set the candidate attributes.

        This implementation generates the candidate attributes from the columns
        of the DataFrame, ignoring the browser_id and time_of_collect fields.
        """
        self._candidate_attributes = AttributeSet()
        for column_id, column in enumerate(self._dataframe.columns, 1):
            attribute = Attribute(column_id, column)
            self._candidate_attributes.add(attribute)
