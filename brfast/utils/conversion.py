#!/usr/bin/python3
"""Module containing utilities to check or convert Python objects."""


def is_str_float(str_value: str) -> bool:
    """Check whether a string value is a float.

    Args:
        str_value: The string value to check.

    Returns:
        Whether the string value can be cast to a float or not.
    """
    try:
        float(str_value)
        return True
    except ValueError:
        return False
