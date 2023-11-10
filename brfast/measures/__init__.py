#!/usr/bin/python3
"""Module containing the interfaces of the measure functions."""

import csv
from typing import Any, Dict, List, Tuple

from loguru import logger

from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset


class UsabilityCostMeasure:
    """The interface of the usability cost measure."""

    def __init__(self):
        """Initialize the usability cost measure."""

    def __repr__(self) -> str:
        """Provide a string representation of this usability cost measure.

        Returns:
            A string representation of this usability cost measure.
        """
        return f'{self.__class__.__name__}'

    def evaluate(self, attribute_set: AttributeSet) -> Tuple[float,
                                                             Dict[str, float]]:
        """Measure the usability cost of an attribute set.

        The usability cost measure is required to be strictly increasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which cost is to be measured.

        Returns:
            A pair with the cost and its explanation. The cost is a numerical
            value whereas the explanation is a dictionary associating a cost
            dimension (str) to a cost value (float).
        """
        raise NotImplementedError


class SensitivityMeasure:
    """The interface of the sensitivity measure."""

    def __init__(self):
        """Initialize the sensitivity measure."""

    def __repr__(self) -> str:
        """Provide a string representation of this sensitivity measure.

        Returns:
            A string representation of this sensitivity measure.
        """
        return f'{self.__class__.__name__}'

    def evaluate(self, attribute_set: AttributeSet) -> float:
        """Measure the sensitivity of an attribute set.

        The sensitivity measure is required to be monotonously decreasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which sensitivity is to be
                           measured.

        Returns:
            The sensitivity of the attribute set.
        """
        raise NotImplementedError


class Analysis:
    """An interface to represent an analysis of a fingerprint dataset."""

    def __init__(self, dataset: FingerprintDataset):
        """Initialize the analysis.

        Args:
            dataset: The fingerprint dataset to analyze.
        """
        self._dataset = dataset
        self._result = {}

    def execute(self):
        """Execute the analysis.

        Raises:
            NotImplementedError: This abstract method is not defined.
        """
        raise NotImplementedError

    @property
    def result(self) -> Dict:
        """Give the result as a dictionary.

        Returns.
            The result as a dictionary. Empty if not yet executed.
        """
        return self._result

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        raise NotImplementedError

    def save_csv_result(self, output_path: str):
        """Save the csv result.

        Args:
            output_path: The file where to write the csv result.
        """
        row_list = self._from_dict_to_row_list()
        logger.debug(f'Saving {self.__class__.__name__} csv result to '
                     f'{output_path}.')
        with open(output_path, 'w+') as csv_output_file:
            csv_output_writer = csv.writer(csv_output_file)
            for row in row_list:
                csv_output_writer.writerow(row)
