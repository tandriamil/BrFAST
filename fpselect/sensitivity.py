#!/usr/bin/python3
"""Module containing the interface of the sensitivity functions."""

from typing import TypeVar


class SensitivityFunction:
    """The interface of the sensitivity function."""

    def __init__(self):
        """Initializes the sensitivity function."""
        pass

    def measure(self, attribute_set: set) -> float:
        """Measures the sensitivity of an attribute set.

        Args:
            attribute_set: The attribute set whose sensitivity is to be
              measured.

        Returns:
            The sensitivity considering this attribute set.
        """
        raise NotImplementedError
