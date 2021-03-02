#!/usr/bin/python3
"""Module containing the interface of the cost functions."""

from fpselect.attribute import Attribute


class Cost:
    """The interface of the cost."""

    def __init__(self, value: float, description: dict):
        """Initializes the cost description."""
        self._value = value
        self._description = description

    def get_value(self) -> float:
        """Gets the value.

        Returns:
            The value of the cost.
        """
        return self._value

    def get_description(self) -> dict:
        """Gets the description.

        Returns:
            The description of the cost.
        """
        return self._description


class CostFunction:
    """The interface of the cost function."""

    def __init__(self):
        """Initializes the cost function."""
        pass

    def measure(self, attribute_set: set[Attribute]) -> Cost:
        """Measures the cost of an attribute set.

        Args
        attribute_set: The set of attributes whose cost is to be measured.

        Returns:
            A Cost object containing the value and description of the cost.
        """
        raise NotImplementedError
