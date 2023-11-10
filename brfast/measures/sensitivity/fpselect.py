#!/usr/bin/python3
"""Module containing the sensitivity measures used in the FPSelect paper."""

import importlib
from typing import List

from loguru import logger

from brfast.config import params
from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.measures import SensitivityMeasure

# from measures.similarity import TODO

# Import the engine of the analysis module (pandas or modin)
pd = importlib.import_module(params.get('DataAnalysis', 'engine'))

PROPORTION_FIELD = 'proportion'


def _get_top_k_fingerprints(dataframe: pd.DataFrame,
                            attribute_names: List[str], k: int
                            ) -> pd.DataFrame:
    """Get a DataFrame with the k-most common fingerprints.

    Args:
        dataframe: The fingerprint dataset.
        attribute_names: The name of the attributes to consider.
        k: The parameter to specify the k-most common fingerprints to hold.

    Returns:
        A DataFrame with only the most common fingerprints together with the
        proportion of the users that share them.
    """
    # Project the dataframe on the wanted attributes
    projected_dataframe = dataframe[attribute_names]

    # Store the current dtypes of each column (needed to put back the dtypes,
    # see below)
    current_column_dtypes = {}
    for column, dtype in projected_dataframe.dtypes.items():
        current_column_dtypes[column] = dtype

    # 1. We have to convert to strings due to the NaN values not being counted
    #    by the value_counts() function!
    # 2. Use the value_counts function to count the unique/distinct rows.
    #    - Each distinct fingerprint is assigned the number of rows
    #      (= browsers) that share it.
    #    - The rows are sorted in descending manner: the most shared
    #      fingerprints are firsts.
    #    - The count is normalized: we have the proportion of users.
    # 2. Rename the normalized count column as "proportion".
    # 3. Only hold the k-most common/shared fingerprints.
    # 4. Put back the previous dtypes of each column
    return (projected_dataframe
            .astype('str')
            .value_counts(normalize=True, sort=True, ascending=False)
            .reset_index(name=PROPORTION_FIELD)
            .head(k)
            .astype(current_column_dtypes)
            )


# class SimilarAttributes(SensitivityMeasure):
#     """The sensitivity measure used in the FPSelect paper.
#
#     This sensitivity measure considers that the impersonated users are those
#     that have a fingerprint that is similar to the one of the k-most common
#     fingerprints. Two fingerprints are considered similar if all their
#     attributes are deemed similar using a similarity function.
#     """
#
#     def __init__(self, fingerprint_dataset: FingerprintDataset,
#                  most_common_fps: int,
#                  attr_dist_info: Dict[str, Dict[str, Any]]):
#         """Initialize the sensitivity measure used in the FPSelect paper.
#
#         Args:
#             dataset: The fingerprint dataset.
#             most_common_fps: The number of the most common fingerprints that
#                              we should consider.
#             attr_dist_info: The information about the attribute distances.
#                             For each attribute as a key, it should contain
#                             the type of the attribute and its TODO
#         """
#         # Initialize using the __init__ function of SensitivityMeasure
#         super().__init__()
#
#         # Set the variables used to compute the sensitivity
#         self._fingerprint_dataset = fingerprint_dataset
#         self._working_dataframe = (
#             fingerprint_dataset.get_df_w_one_fp_per_browser())
#         self._k = most_common_fps
#         self._attr_dist_info = attr_dist_info
#
#     def __repr__(self) -> str:
#         """Provide a string representation of this sensitivity measure.
#
#         Returns:
#             A string representation of this sensitivity measure.
#         """
#         return (f'{self.__class__.__name__}({self._fingerprint_dataset}, '
#                 f'{self._k})')
#
#     def evaluate(self, attribute_set: AttributeSet) -> float:
#         """Measure the sensitivity of an attribute set.
#
#         The sensitivity measure is required to be monotonously decreasing as
#         we add attributes (see the FPSelect paper).
#
#         Args:
#             attribute_set: The attribute set which sensitivity is to be
#                            measured.
#
#         Returns:
#             The sensitivity of the attribute set.
#         """
#         # Get the names of the attributes that we consider
#         attribute_names = [attribute.name for attribute in attribute_set]
#
#         # Project these attributes on the fingerprint dataset
#         projected_fingerprints = self._working_dataframe[attribute_names]
#
#         # Get the k-most common/shared fingerprints
#         top_k_fingerprints = _get_top_k_fingerprints(
#             projected_fingerprints, attribute_names, self._k)
#
#         # Return the proportion of users having a fingerprint that is similar
#         # to the k-most common fingerprints considering similarity functions
#         # return _get_proportion_similar_fingerprints(
#         #     projected_fingerprints, top_k_fingerprints)
#         return None


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
            fingerprint_dataset: The fingerprint dataset.
            most_common_fps: The number of the most common fingerprints that we
                             should consider.
        """
        # Initialize using the __init__ function of SensitivityMeasure
        super().__init__()

        # Set the variables used to compute the sensitivity
        self._fingerprint_dataset = fingerprint_dataset
        self._working_dataframe = (
            fingerprint_dataset.get_df_w_one_fp_per_browser())
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
            self._working_dataframe, attribute_names, self._k)
        browsers_sharing_top_k_fps = top_k_fingerprints[PROPORTION_FIELD].sum()
        logger.debug(f'The top {self._k} fingerprints are shared by '
                     f'{browsers_sharing_top_k_fps} of the browsers.')

        # Return the proportion of users sharing the k-most common fingerprints
        return browsers_sharing_top_k_fps
