#!/usr/bin/python3
"""Measures of the instability of the attribues of a fingerprint dataset."""

from typing import Any, List

from brfast import config
from brfast.data import MetadataField
from brfast.measures import Analysis


class ProportionOfChanges(Analysis):
    """Measure the average instability of the attributes of a dataset."""

    def execute(self):
        """Execute the analysis.

        Raises:
            NotImplementedError: This abstract method is not defined.

        Note:
            This measure does not use modin due to a bug where no comparisons
            are retrieved.
        """
        dataframe = self._dataset.dataframe

        # Force to use pandas.DataFrame due to a bug
        if config['DataAnalysis']['engine'] == 'modin.pandas':
            dataframe = dataframe._to_pandas()

        # 1. Group by the browser id (no sort for performances, no group key to
        #    not add an additonal column with the group key)
        # 2. Sort by the time of collection for each group (give a DataFrame)
        # 3. Regroup by the browser id, here each group has the fingerprints
        #    sorted by the time of collection
        grouped_by_browser = (
            dataframe
            .groupby(MetadataField.BROWSER_ID, sort=False, group_keys=False)
            .apply(lambda group_df: group_df.sort_values(
                MetadataField.TIME_OF_COLLECT))
            .groupby(MetadataField.BROWSER_ID, sort=False, group_keys=False))

        # For each attribute, we compute its instability as the proportion of
        # value changes over the number of comparisons (= pairs of consecutive
        # fingerprints)
        for attribute in self._dataset.candidate_attributes:
            comparisons, changes = 0, 0

            # Each group contains the consecutive fingerprints of a browser
            for _, fingerprints_df in grouped_by_browser:

                # Get the Series of the values of the attribute
                attribute_values = fingerprints_df[attribute.name]

                # For each value and the next one. For three values v1, v2, v3,
                # we then compare (v1, v2) and (v2, v3)
                for value, next_value in zip(attribute_values,
                                             attribute_values[1:]):
                    comparisons += 1
                    if value != next_value:
                        changes += 1

            self._result[attribute] = changes / comparisons

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = [['attribute', 'proportion_of_changes']]  # The header
        for attribute, instability in self._result.items():
            row_list.append([attribute.name, instability])
        return row_list
