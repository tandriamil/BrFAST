#!/usr/bin/python3
"""Module containing the collection of a fingerprint subset."""

from typing import Any, List

from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.measures import Analysis


class AttributeSetSample(Analysis):
    """Sample of the fingerprints considering a subset of the attributes."""

    def __init__(self, dataset: FingerprintDataset, attributes: AttributeSet,
                 sample_size: int):
        """Initialize the analysis.

        Args:
            dataset: The fingerprint dataset to analyze.
            attributes: The attributes to consider.
            sample_size: The size of the sample that we are interested in,
                         reqired to be strictly positive.

        Raises:
            AttributeError: The sample size is required to be a strictly
                            positive number.
        """
        super().__init__(dataset)
        self._attributes = attributes
        if sample_size < 1:
            raise AttributeError('The sample size is required to be a strictly'
                                 ' positive number.')
        self._sample_size = sample_size

    def execute(self):
        """Execute the analysis.

        Raises:
            ValueError: The attribute set or the fingerprint dataset is empty.
                        The provided sample is higher than the dataset size.
        """
        if not self._attributes or self._dataset.dataframe.empty:
            raise ValueError('The attribute set of the fingerprint dataset '
                             'should not be empty.')

        attribute_names = self._attributes.attribute_names
        # 1. Project the dataframe on the wanted columns.
        # 2. Get a sample of the provided size.
        # 3. Obtain the records: we get a list of rows with the attribute
        #    values as a tuple.
        fingerprints = (self._dataset.dataframe[attribute_names]
                        .sample(self._sample_size)
                        .to_records(index=False))
        for row_id, fingerprint in enumerate(fingerprints):
            self._result[row_id] = tuple(fingerprint)

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = []
        row_list.append(self._dataset.candidate_attributes.attribute_names)
        for fingerprint in self._result.values():
            row_list.append(fingerprint)
        return row_list
