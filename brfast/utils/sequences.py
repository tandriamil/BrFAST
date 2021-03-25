#!/usr/bin/python3
"""Module containing utilities when using sequences."""

from typing import Any, List, Tuple


def sort_dict_by_value(dictionary: dict, reverse: bool = False
                       ) -> List[Tuple[Any, Any]]:
    """Sort a dictionary by the values which have to be sortable.

    Args:
        dictionary: The dictionary to sort.
        reverse: Whether we sort in reverse order (highest to lowest).

    Returns:
        A list of (key, value) pairs of the dictionary sorted by the values.
    """
    return sorted(dictionary.items(), key=lambda x: x[1], reverse=reverse)
