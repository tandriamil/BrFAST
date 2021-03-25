#!/usr/bin/python3
"""Module containing the sensitivity measures used in the FPSelect paper."""

from typing import Any, Dict, List

import pandas as pd

from brfast.data import (AttributeSet, FingerprintDataset, MetadataField)
from brfast.measures import SensitivityMeasure
# from measures.similarity import TODO

PROPORTION_FIELD = 'proportion'


def _get_top_k_fingerprints(dataset: pd.DataFrame, attribute_names: List[str],
                            k: int) -> pd.DataFrame:
    """Get a DataFrame with the k-most common fingerprints.

    Args:
        dataset: The fingerprint dataset.
        attribute_names: The name of the attributes to consider.
        k: The parameter to specify the k-most common fingerprints to hold.

    Returns:
        A DataFrame with only the most common fingerprints together with the
        proportion of the users that share them.
    """
    # 1. Use the value_counts function to count the unique/distinct rows.
    #    - Each distinct fingerprint is assigned the number of rows
    #      (= browsers) that share it.
    #    - The rows are sorted in descending manner: the most shared
    #      fingerprints are firsts.
    #    - The count is normalized: we have the proportion of users.
    # 2. Rename the normalized count column as "proportion".
    # 3. Only hold the k-most common/shared fingerprints.
    return (dataset.value_counts(attribute_names, normalize=True)
                   .reset_index(name=PROPORTION_FIELD)
                   .head(k))


def _preprocess_one_fp_per_browser(dataframe: pd.DataFrame,
                                   last_fingerprint: bool = True
                                   ) -> pd.DataFrame:
    """Preprocess a fingerprint dataset used for the sensitivity measures.

    The preprocessing only holds the first (or last) fingerprint of each user.

    Args:
        dataframe: The fingerprint dataset.
        last_fingerprint: Whether we should only hold the last fingerprint of
                          each user, otherwise it is the first fingerprint.

    Returns:
        A clean dataset that is used for the sensitivity measure having only
        one fingerprint for each browser.
    """
    # If the dataframe is empty, just return it
    if dataframe.empty:
        return dataframe

    # 1. We group the fingerprints (=rows) by the browser id. As we do not care
    #    about the order of the browser ids, we turn the sorting off for
    #    better performances. We need to disable the group keys to not have an
    #    additional index with the value of the index 'browser_id'.
    grouped_by_browser = dataframe.groupby(MetadataField.BROWSER_ID,
                                           sort=False, group_keys=False)

    # 2. For each group (= a browser id), we sort the fingerprints by the time
    #    they were collected at. If we want the last fingerprint, then we sort
    #    them in descending manner (= not ascending) to have the latest first.
    # 3. We only hold a fingerprint for each group, hence for each browser.
    return grouped_by_browser.apply(
        lambda row: row.sort_values(MetadataField.TIME_OF_COLLECT,
                                    ascending=not last_fingerprint)
                       .head(1))


class SimilarAttributes(SensitivityMeasure):
    """The sensivity measure used in the FPSelect paper.

    This sensitivity measure considers that the impersonated users are those
    that have a fingerprint that is similar to the one of the k-most common
    fingerprints. Two fingerprints are considered similar if all their
    attributes are deemed similar using a similarity function.
    """

    def __init__(self, fingerprint_dataset: FingerprintDataset,
                 most_common_fps: int,
                 attr_dist_info: Dict[str, Dict[str, Any]]):
        """Initialize the sensivity measure used in the FPSelect paper.

        Args:
            dataset: The fingerprint dataset.
            most_common_fps: The number of the most common fingerprints that we
                             should consider.
            attr_dist_info: The information about the attribute distances. For
                            each attribute as a key, it should contain the
                            type of the attribute and its
        """
        # Initialize using the __init__ function of SensitivityMeasure
        super().__init__()

        # Set the variables used to compute the sensitivity
        self._fingerprint_dataset = fingerprint_dataset
        self._working_dataset = _preprocess_one_fp_per_browser(
            fingerprint_dataset.dataset)
        self._k = most_common_fps
        self._attr_dist_info = attr_dist_info

    def __repr__(self) -> str:
        """Provide a string representation of this sensitivity measure.

        Returns:
            A string representation of this sensitivity measure.
        """
        return (f'{self.__class__.__name__}({self._fingerprint_dataset}, '
                f'{self._k})')

    def evaluate(self, attribute_set: AttributeSet) -> float:
        """Measure the sensitivity of an attribute set.

        The sensitivity measure is required to be monotonously decreasing as we
        add attributes (see the FPSelect paper).

        Args:
            attribute_set: The attribute set which sensitivity is to be
                           measured.

        Returns:
            The sensitivity of the attribute set.
        """
        # Get the names of the attributes that we consider
        attribute_names = [attribute.name for attribute in attribute_set]

        # Project these attributes on the fingerprint dataset
        projected_fingerprints = self._working_dataset[attribute_names]

        # Get the k-most common/shared fingerprints
        top_k_fingerprints = _get_top_k_fingerprints(
            projected_fingerprints, attribute_names, self._k)

        # Return the proportion of users having a fingerprint that is similar
        # to the k-most common fingerprints considering similarity functions
        # TODO
        # return _get_proportion_similar_fingerprints(
        #     projected_fingerprints, top_k_fingerprints)
        return None


class TopKFingerprints(SensitivityMeasure):
    """Simple sensitivity measure considering the k-most common fingerprints.

    This sensitivity measure considers that the impersonated users are those
    that share the k-most common fingerprints. No similarity function is
    considered here.
    """

    def __init__(self, fingerprint_dataset: FingerprintDataset,
                 most_common_fps: int):
        """Initialize the top-k simple sensitivity measure.

        Args:
            dataset: The fingerprint dataset.
            most_common_fps: The number of the most common fingerprints that we
                             should consider.
        """
        # Initialize using the __init__ function of SensitivityMeasure
        super().__init__()

        # Set the variables used to compute the sensitivity
        self._fingerprint_dataset = fingerprint_dataset
        self._working_dataset = _preprocess_one_fp_per_browser(
            fingerprint_dataset.dataset)
        self._k = most_common_fps

    def __repr__(self) -> str:
        """Provide a string representation of this sensitivity measure.

        Returns:
            A string representation of this sensitivity measure.
        """
        return (f'{self.__class__.__name__}({self._fingerprint_dataset}, '
                f'{self._k})')

    def evaluate(self, attribute_set: AttributeSet) -> float:
        """Measure the sensitivity of an attribute set.

        The sensitivity measure is required to be monotonously decreasing as we
        add attributes (see the FPSelect paper).

        Args:
            attribute_set: The attribute set which sensitivity is to be
                           measured.

        Returns:
            The sensitivity of the attribute set.
        """
        # Get the names of the attributes that we consider
        attribute_names = [attribute.name for attribute in attribute_set]

        # Get the k-most common/shared fingerprints
        top_k_fingerprints = _get_top_k_fingerprints(
            self._working_dataset, attribute_names, self._k)

        # Return the proportion of users sharing the k-most common fingerprints
        return top_k_fingerprints[PROPORTION_FIELD].sum()