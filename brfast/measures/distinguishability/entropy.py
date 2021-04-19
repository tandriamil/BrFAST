#!/usr/bin/python3
"""Module containing the entropy measures of attribute sets."""

from math import log2
from typing import Any, List

from loguru import logger
from scipy.stats import entropy

from brfast import config
from brfast.data import AttributeSet, FingerprintDataset
from brfast.measures import Analysis


ENTROPY_BASE = 2

COUNT_FIELD = '__count_field__'
ENTROPY_RESULT = 'entropy'
MAXIMUM_ENTROPY_RESULT = 'maximum_entropy'
NORMALIZED_ENTROPY_RESULT = 'normalized_entropy'


def attribute_set_entropy(fingerprint_dataset: FingerprintDataset,
                          attribute_set: AttributeSet):
    """Compute the entropy of a dataset considering the given attribute set.

    Args:
        fingerprint_dataset: The dataset used to compute the entropy.
        attribute_set: The non-empty attribute set that is considered when
                       computing the entropy of the fingerprints.

    Returns:
        The entropy of the fingerprints considering this attribute set.

    Raises:
        ValueError: The attribute set is empty, no grouping is possible.
        KeyError: An attribute is not in the fingerprint dataset.

    Note:
        This function is forced to use pandas as the data analysis engine.
    """
    considered_attribute_names = [attribute.name
                                  for attribute in attribute_set]

    # We will work on a dataset with only a fingerprint per browser to
    # avoid overcounting effects
    df_one_fp_per_browser = fingerprint_dataset.get_df_w_one_fp_per_browser()

    # If using modin, switch back to pandas
    if config['DataAnalysis']['engine'] == 'modin.pandas':
        logger.warning('The attribute_set_entropy function badly supports the '
                       'modin engine. We switch back to pandas in this '
                       'function.')
        df_one_fp_per_browser = df_one_fp_per_browser._to_pandas()

    # 1. Count the occurences of each distinct fingerprint
    # 2. Name the count column as COUNT_FIELD
    # 3. Project on the count column to obtain a Serie such that each value
    #    is the number of browsers sharing a given fingerprint
    # 4. Sum to obtain the total number of fingerprints
    distinct_value_count = (df_one_fp_per_browser
                            .value_counts(considered_attribute_names,
                                          normalize=True, sort=False)
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
        """Execute the analysis."""
        # We will work on a dataset with only a fingerprint per browser to
        # avoid overcounting effects
        df_one_fp_per_browser = self._dataset.get_df_w_one_fp_per_browser()

        # Compute the entropy of the fingerprints given this attribute set
        attr_set_entropy = attribute_set_entropy(self._dataset,
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
