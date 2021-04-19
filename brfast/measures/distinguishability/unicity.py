#!/usr/bin/python3
"""Module containing the unicity measures."""

from typing import Any, List

from loguru import logger

from brfast.data import AttributeSet, FingerprintDataset
from brfast.measures import Analysis

COUNT_FIELD = 'count_field'
UNIQUE_FPS_RESULT = 'unique_fingerprints'
UNICITY_RATE_RESULT = 'unicity_rate'
TOTAL_BROWSERS_RESULT = 'total_browsers'


class AttributeSetUnicity(Analysis):
    """Compute the unicity of the fingerprints considering an attribute set."""

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
        attribute_names = self._attributes.attribute_names

        # We will work on a dataset with only a fingerprint per browser to
        # avoid overcounting effects
        df_one_fp_per_browser = self._dataset.get_df_w_one_fp_per_browser()

        # Count the total number of browsers
        total_browsers = len(df_one_fp_per_browser)

        # 1. Count the occurences of each distinct fingerprint
        # 2. Name the count column as COUNT_FIELD
        # 3. Project on the count column to obtain a Serie such that each value
        #    is the number of browsers sharing a given fingerprint
        # 4. Sum to obtain the total number of fingerprints
        fingerprint_occurences = (df_one_fp_per_browser
                                  .value_counts(attribute_names, sort=False)
                                  .reset_index(name=COUNT_FIELD)
                                  [COUNT_FIELD])

        # Compute the number of unique fingerprints
        unique_fingerprints = (fingerprint_occurences
                               [fingerprint_occurences == 1]
                               .sum())

        # Store the results
        self._result[UNIQUE_FPS_RESULT] = unique_fingerprints
        logger.debug(f'Computed {UNIQUE_FPS_RESULT}: {unique_fingerprints}')

        unicity_rate = unique_fingerprints / total_browsers
        self._result[UNICITY_RATE_RESULT] = unicity_rate
        logger.debug(f'Computed {UNICITY_RATE_RESULT}: {unicity_rate}')

        self._result[TOTAL_BROWSERS_RESULT] = total_browsers
        logger.debug(f'Computed {TOTAL_BROWSERS_RESULT}: {total_browsers}')

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
