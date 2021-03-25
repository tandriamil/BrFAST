#!/usr/bin/python3
"""Module containing the interfaces of the measure functions."""

from typing import Dict, Tuple

from brfast.data import AttributeSet


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
