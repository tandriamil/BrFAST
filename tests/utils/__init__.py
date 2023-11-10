#!/usr/bin/python3
"""Init file of the tests.utils module."""

from typing import Any


def remove_key_if_present(dictionary: dict, key: Any):
    """Remove a key from a dictionary if it is present.

    Args:
        dictionary: The dictionary from which to remove the key.
        key: The key to remove if present. If a list, it goes over the keys
             recursively (at least two elements required).
    """
    if isinstance(key, list):
        current_dictionary = dictionary
        for current_key in key[:-1]:
            if current_key in current_dictionary:
                current_dictionary = current_dictionary[current_key]
            else:
                return  # If one of the keys is not present, we end here

        # We reached the end, i.e., the last key is in the dictionary
        last_key = key[-1]
        if last_key in current_dictionary:
            del current_dictionary[last_key]
    else:
        if key in dictionary:
            del dictionary[key]
