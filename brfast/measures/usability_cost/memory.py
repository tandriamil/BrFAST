#!/usr/bin/python3
"""Measures of the average size of the attributes of a fingerprint dataset."""

from typing import Any, List

from brfast.measures import Analysis


class AverageFingerprintSize(Analysis):
    """Measure the average fingerprint size of the attributes of a dataset."""

    def execute(self):
        """Execute the analysis.

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        for attribute in self._dataset.candidate_attributes:
            # 1. Project the dataframe on the attribute (get Series)
            # 2. Map the values of this attribute to their length
            # 3. Obtain the average of the sizes
            average_size = (self._dataset.dataframe[attribute.name]
                            .apply(lambda value: len(str(value)))
                            .mean())
            self._result[attribute] = average_size

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = [['attribute', 'average_size']]  # The header
        for attribute, average_size in self._result.items():
            row_list.append([attribute.name, average_size])
        return row_list
