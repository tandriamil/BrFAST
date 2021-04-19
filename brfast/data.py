#!/usr/bin/python3
"""Module containing the interfaces related to the fingerprint dataset."""

import importlib
from io import TextIOWrapper
from os import path
from threading import Lock
from typing import Iterable, List, Optional

from loguru import logger
from sortedcontainers import SortedDict

# Import the engine of the analysis module (pandas or modin)
from brfast import config
pd = importlib.import_module(config['DataAnalysis']['engine'])


# ============================== Utility classes ==============================
class MetadataField:
    """Class representing the required metadata fields."""

    BROWSER_ID = 'browser_id'
    TIME_OF_COLLECT = 'time_of_collect'
    ALL = {BROWSER_ID, TIME_OF_COLLECT}


class MissingMetadatasFields(Exception):
    """The required metadatas columns are missing from the dataset."""


# ========================= Attribute related classes =========================
class Attribute:
    """
    The Attribute class to represent an attribute.

    The attributes should have a unique identifier.
    """

    def __init__(self, attr_id: int, name: str):
        """Initialize the Attribute object with its id and name.

        Args:
            attr_id: The unique id of the attribute.
            name: The name of the attribute
        """
        self._attr_id = attr_id
        self._name = name

    def __repr__(self) -> str:
        """Provide a string representation of this attribute.

        Returns:
            A string representation of this attribute.
        """
        return f'{self.__class__.__name__}({self._attr_id}, {self._name})'

    @property
    def attr_id(self) -> int:
        """Give the id of the attribute (read only).

        Returns:
            The id of the attribute.
        """
        return self._attr_id

    @property
    def name(self) -> str:
        """Give the name of the attribute (read only).

        Returns:
            The name of the attribute.
        """
        return self._name

    def __hash__(self) -> int:
        """Give the hash of an attribute, which is simply its id."""
        return self._attr_id

    def __eq__(self, other_attribute: 'Attribute') -> bool:
        """Compare two attributes which are equal if they have the same id.

        Returns:
            The attributes are the same (i.e., they share the same id).
        """
        return (isinstance(other_attribute, self.__class__)
                and self._attr_id == other_attribute.attr_id)


class AttributeSet:
    """The AttributeSet interface to represent an attribute set."""

    def __init__(self, attributes: Optional[Iterable[Attribute]] = None):
        """Initialize the AttributeSet object with the attributes.

        Args:
            attributes: The attributes composing this set or empty if none.
        """
        # Maintain a sorted dictionary of attributes id to the actual attribute
        self._id_to_attr = SortedDict()
        if attributes:
            for attribute in attributes:
                self._id_to_attr[attribute.attr_id] = attribute

    def __iter__(self):
        """Give the iterator for the AttributeSet to get the attributes."""
        return iter(self._id_to_attr.values())

    def __repr__(self) -> str:
        """Provide a string representation of this attribute set.

        Returns:
            A string representation of this attribute set.
        """
        attribute_list = ', '.join(str(attr)
                                   for attr in self._id_to_attr.values())
        return f'{self.__class__.__name__}([{attribute_list}])'

    @property
    def attribute_names(self) -> List[str]:
        """Give the names of the attributes of this attribute set (read only).

        The attribute names are sorted in function of the attribute id.

        Returns:
            The name of the attributes of this attribute set as a list of str.
        """
        return [attribute.name for attribute in self._id_to_attr.values()]

    @property
    def attribute_ids(self) -> List[int]:
        """Give the ids of the attributes of this attribute set (read only).

        Returns:
            The ids of the attributes of this set as a sorted list of integers.
        """
        return list(self._id_to_attr.keys())

    def add(self, attribute: Attribute):
        """Add an attribute to this attribute set if it is not already present.

        Args:
            attribute: The attribute to add.
        """
        if attribute.attr_id not in self._id_to_attr:
            self._id_to_attr[attribute.attr_id] = attribute

    def remove(self, attribute: Attribute):
        """Remove an attribute from this attribute set.

        Args:
            attribute: The attribute to remove.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        if attribute.attr_id not in self._id_to_attr:
            raise KeyError(f'{attribute} is not among the attributes.')
        del self._id_to_attr[attribute.attr_id]

    def __hash__(self) -> int:
        """Give the hash of an attribute set: the hash of its attributes.

        Returns:
            The hash of an attribute set as the hash of its frozen attributes.
        """
        return hash(frozenset(self.attribute_ids))

    def __eq__(self, other_attr_set: 'AttributeSet') -> bool:
        """Compare two attribute sets, equal if the attributes correspond.

        Returns:
            The two attribute sets are equal: they share the same attributes.
        """
        return (isinstance(other_attr_set, self.__class__)
                and hash(self) == hash(other_attr_set))

    def __contains__(self, attribute: Attribute) -> bool:
        """Check if the attribute is in this attribute set.

        Returns:
            The attribute is in this attribute set.
        """
        return attribute.attr_id in self._id_to_attr

    def __len__(self) -> int:
        """Give the size of this attribute set as the number of attributes.

        Returns:
            The number of attributes in this attribute set.
        """
        return len(self._id_to_attr)

    def issuperset(self, attribute_set: 'AttributeSet') -> bool:
        """Check if this attribute set is a superset of another one.

        Returns:
            This attribute set is a superset of attribute_set.
        """
        self_attribute_ids_set = frozenset(self.attribute_ids)
        attribute_ids_set = frozenset(attribute_set.attribute_ids)
        return self_attribute_ids_set.issuperset(
            attribute_ids_set)

    def issubset(self, attribute_set: 'AttributeSet') -> bool:
        """Check if this attribute set is a subset of another one.

        Returns:
            This attribute set is a subset of attribute_set.
        """
        self_attribute_ids_set = frozenset(self.attribute_ids)
        attribute_ids_set = frozenset(attribute_set.attribute_ids)
        return self_attribute_ids_set.issubset(
            attribute_ids_set)

    def get_attribute_by_id(self, attr_id: int) -> Attribute:
        """Give an attribute by its id.

        Args:
            attr_id: The id of the attribute to retrieve.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        if attr_id not in self._id_to_attr:
            raise KeyError(f'No attribute with the id {attr_id}.')
        return self._id_to_attr[attr_id]

    def get_attribute_by_name(self, name: str) -> Attribute:
        """Give an attribute by its name.

        Args:
            name: The name of the attribute to retrieve.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        for attribute in self._id_to_attr.values():
            if attribute.name == name:
                return attribute
        raise KeyError(f'No attribute is named {name}.')


# ==================== Fingerprint dataset related classes ====================
class FingerprintDataset:
    """A fingerprint dataset (abstract class)."""

    def __init__(self):
        """Initialize."""
        self._dataframe, self._candidate_attributes = None, None

        # The dataframes with a single fingerprint per browser, lazily computed
        self._first_fp_df, self._last_fp_df = None, None

        # The locks related to the previous dataframes, as Flask is
        # multithreaded and the access of this data can be parallel in some GET
        # requests
        self._first_fp_df_lock, self._last_fp_df_lock = Lock(), Lock()

        # Process the dataset
        self._process_dataset()

        # Check that the necessary metadatas are present
        required_metadatas = MetadataField.ALL
        if any((not isinstance(self._dataframe.index, pd.MultiIndex),
                not required_metadatas.issubset(self._dataframe.index.names))):
            raise MissingMetadatasFields(
                'The required metadata fields and indices '
                f'{required_metadatas} are missing from the dataset.')

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
          indices being  browser_id (int64) and time_of_collect (datetime64).
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

            # Do this inside the lock due to multithreading
            self._last_fp_df_lock.acquire()
            try:
                logger.debug('Acquired the _last_fp_df_lock lock')
                if self._last_fp_df is None:
                    logger.debug(f'Generate the dataframe {self} with the last'
                                 ' fingerprint only for each browser')
                    self._last_fp_df = self._preprocess_one_fp_per_browser(
                        last_fingerprint)
            finally:
                self._last_fp_df_lock.release()
                logger.debug('Released the _last_fp_df_lock lock')

            # Return the resulting DataFrame
            return self._last_fp_df

        # First fingerprint
        logger.debug(f'Getting the dataframe {self} with the first '
                     'fingerprint only for each browser')

        # Do this inside the lock due to multithreading
        self._first_fp_df_lock.acquire()
        try:
            logger.debug('Acquired the _first_fp_df_lock lock')
            if self._first_fp_df is None:
                logger.debug(f'Generate the dataframe {self} with the first '
                             'fingerprint only for each browser')
                self._first_fp_df = self._preprocess_one_fp_per_browser(
                    last_fingerprint)
        finally:
            self._first_fp_df_lock.release()
            logger.debug('Released the _last_fp_df_lock lock')

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

    def __init__(self, dataset_path: str):
        """Initialize the FingerprintDataset with the path to the dataset.

        Args:
            dataset_path: The path to the fingerprint dataset.

        Raises:
            FileNotFoundError: There is not file at the given dataset path.
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
          indices being  browser_id (int64) and time_of_collect (datetime64).
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
    def dataset_path(self) -> str:
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
          indices being  browser_id (int64) and time_of_collect (datetime64).
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

        # Set the indices as 'browser_id' and 'time_of_collect'
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


class FingerprintDatasetFromCSVInMemory(FingerprintDataset):
    """A fingerprint dataset read from a in memory csv file."""

    def __init__(self, file_handle: TextIOWrapper):
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
          indices being  browser_id (int64) and time_of_collect (datetime64).
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

        # Set the indices as 'browser_id' and 'time_of_collect'
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)

    def _set_candidate_attributes(self):
        """Set the candidate attributes.

        This implementation generates the candidate attributes from the columns
        of the DataFrame, ignoring the browser_id and time_of_collect fields.
        """
        self._candidate_attributes = AttributeSet()
        for column_id, column in enumerate(self._dataframe.columns, 1):
            attribute = Attribute(column_id, column)
            self._candidate_attributes.add(attribute)
