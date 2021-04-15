#!/usr/bin/python3
"""Module containing utilities when manipulating files."""

from os import mkdir, path


def create_directory_if_not_exists(directory_path: str):
    """Create a directory if it does not exist.

    Args:
        directory_path: The path to the directory to create.
    """
    if not path.exists(directory_path):
        mkdir(directory_path)
