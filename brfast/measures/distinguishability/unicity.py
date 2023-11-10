#!/usr/bin/python3
"""Module containing the unicity measures."""

from typing import Any, List

from loguru import logger

from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.measures import Analysis

COUNT_FIELD = '__count_field__'

# The three information that are stored in the unicity results
UNIQUE_FPS_RESULT = 'unique_fingerprints'
UNICITY_RATE_RESULT = 'unicity_rate'
TOTAL_BROWSERS_RESULT = 'total_browsers'


class AttributeSetUnicity(Analysis):
    """Compute the unicity of the fingerprints considering an attribute set."""

    def __init__(self, dataset: FingerprintDataset, attributes: AttributeSet):
        """Initialize the analysis.

        Args:
            dataset: The non-empty fingerprint dataset to analyze.
            attributes: The non-empty attributes to consider.
        """
        super().__init__(dataset)
        self._attributes = attributes

    def execute(self):
        """Compute the unicity results.

        Raises:
            ValueError: The attribute set or the fingerprint dataset is empty.
            KeyError: An attribute is not in the fingerprint dataset.

        Note:
            For now, pandas does not include a drop na parameter in the
            DataFrame.value_counts() function, hence it always drops the NaN
            values that can be present in our fingerprint dataset. This results
            in these fingerprints being ignored when counting the unique
            fingerprints. In the future, if pandas include this parameter,
            better use it instead of casting the values to strings.
        """
        # If an empty dataset of attribute set, we cannot compute the unicity
        if not self._attributes or self._dataset.dataframe.empty:
            raise ValueError('Cannot compute the entropy considering an empty '
                             'dataset or an empty attribute set.')

        # We will work on a dataset with only a fingerprint per browser to
        # avoid over-counting effects
        df_one_fp_per_browser = self._dataset.get_df_w_one_fp_per_browser()

        # Project the dataframe on the wanted attributes
        attribute_names = self._attributes.attribute_names
        projected_dataframe = df_one_fp_per_browser[attribute_names]

        # 1. Convert the values of the attributes as strings for the
        #    fingerprints containing NaN values to not be ignored
        # 2. Count the occurrences of each distinct fingerprint
        # 3. Name the count column as COUNT_FIELD
        # 4. Project on the count column to obtain a Series such that each value
        #    is the number of browsers sharing a given fingerprint
        fingerprint_occurrences = (projected_dataframe
                                   .astype('str')
                                   .value_counts(sort=False)
                                   .reset_index(name=COUNT_FIELD)
                                   [COUNT_FIELD])

        # Compute the number of unique fingerprints
        unique_fingerprints = (fingerprint_occurrences
                               [fingerprint_occurrences == 1]
                               .sum())

        # Count the total number of browsers
        total_browsers = len(projected_dataframe)

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
