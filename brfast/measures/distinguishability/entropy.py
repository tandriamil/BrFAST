#!/usr/bin/python3
"""Module containing the entropy measures of attribute sets."""

import importlib
from math import log2
from typing import Any, List

from loguru import logger
from scipy.stats import entropy

from brfast.config import ANALYSIS_ENGINES, params
from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.measures import Analysis

pd = importlib.import_module(params.get('DataAnalysis', 'engine'))


ENTROPY_BASE = 2

COUNT_FIELD = '__count_field__'
ENTROPY_RESULT = 'entropy'
MAXIMUM_ENTROPY_RESULT = 'maximum_entropy'
NORMALIZED_ENTROPY_RESULT = 'normalized_entropy'


def attribute_set_entropy(df_one_fp_per_browser: pd.DataFrame,
                          attribute_set: AttributeSet) -> float:
    """Compute the entropy of a dataset considering the given attribute set.

    Args:
        df_one_fp_per_browser: The dataframe with only one fingerprint per
                               browser.
        attribute_set: The non-empty attribute set that is considered when
                       computing the entropy of the fingerprints.

    Returns:
        The entropy of the fingerprints considering this attribute set.

    Raises:
        ValueError: The attribute set or the fingerprint dataset is empty.
        KeyError: An attribute is not in the fingerprint dataset.

    Note:
        This function is forced to use pandas as the data analysis engine.
    """
    # If an empty dataset of attribute set, we cannot compute the entropy
    if not attribute_set or df_one_fp_per_browser.empty:
        raise ValueError('Cannot compute the entropy considering an empty '
                         'dataset or an empty attribute set.')

    # If using modin, switch back to pandas
    if params.get('DataAnalysis', 'engine') == ANALYSIS_ENGINES[1]:
        logger.warning('The attribute_set_entropy function badly supports the '
                       'modin engine. We switch back to pandas in this '
                       'function.')
        df_one_fp_per_browser = df_one_fp_per_browser._to_pandas()

    # Project the dataframe on the wanted attributes
    attribute_names = [attribute.name for attribute in attribute_set]
    projected_dataframe = df_one_fp_per_browser[attribute_names]

    # 1. Convert the values of the attributes as strings for the
    #    fingerprints containing NaN values to not be ignored
    # 2. Count the occurrences of each distinct fingerprint
    # 3. Name the count column as COUNT_FIELD
    # 4. Project on the count column to obtain a Series such that each value
    #    is the number of browsers sharing a given fingerprint
    distinct_value_count = (projected_dataframe
                            .astype('str')
                            .value_counts(normalize=True, sort=False)
                            .reset_index(name=COUNT_FIELD)
                            [COUNT_FIELD])

    return entropy(distinct_value_count, base=ENTROPY_BASE)


class AttributeSetEntropy(Analysis):
    """Compute the entropy of the fingerprints considering an attribute set."""

    def __init__(self, dataset: FingerprintDataset, attributes: AttributeSet):
        """Initialize the analysis.

        Args:
            dataset: The fingerprint dataset to analyze.
            attributes: The attributes to consider.
        """
        super().__init__(dataset)
        self._attributes = attributes

    def execute(self):
        """Execute the analysis.

        Raises:
            ValueError: The attribute set or the fingerprint dataset is empty.
            KeyError: An attribute is not in the fingerprint dataset.
        """
        # We will work on a dataset with only a fingerprint per browser to
        # avoid over-counting effects
        df_one_fp_per_browser = self._dataset.get_df_w_one_fp_per_browser()

        # Compute the entropy of the fingerprints given this attribute set
        attr_set_entropy = attribute_set_entropy(df_one_fp_per_browser,
                                                 self._attributes)
        self._result[ENTROPY_RESULT] = attr_set_entropy
        logger.debug(f'Computed {ENTROPY_RESULT}: {attr_set_entropy}')

        # Count the total number of browsers
        total_browsers = len(df_one_fp_per_browser)

        # Compute the maximum entropy of the fingerprints given this attribute
        # set: log2(N) with N the total number of fingerprints
        maximum_entropy = log2(total_browsers)
        self._result[MAXIMUM_ENTROPY_RESULT] = maximum_entropy
        logger.debug(f'Computed {MAXIMUM_ENTROPY_RESULT}: {maximum_entropy}')

        # Compute the normalized entropy
        normalized_entropy = attr_set_entropy / maximum_entropy
        self._result[NORMALIZED_ENTROPY_RESULT] = normalized_entropy
        logger.debug(f'Computed {NORMALIZED_ENTROPY_RESULT}: '
                     f'{normalized_entropy}')

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = []
        for result_name, result_value in self._result.items():
            row_list.append([result_name, result_value])
        return row_list
