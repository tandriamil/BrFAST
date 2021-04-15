#!/usr/bin/python3
"""Utilities to manipulate the files in the Flask webserver."""

ALLOWED_EXTENSIONS = {'csv', 'json'}


def allowed_extension(filename: str, expected_extension: str = None):
    """Check whether a filename is allowed to be received by the server.

    Args:
        filename: The name of the file that was sent.
        expected_extension: The expected extension if there is one.

    Returns:
        Whether the filename is either the expected one if provided, otherwise
        if it is accepted to be received on the server.
    """
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    if expected_extension:
        return extension == expected_extension
    return extension in ALLOWED_EXTENSIONS
