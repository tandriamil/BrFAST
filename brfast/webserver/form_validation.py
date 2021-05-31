#!/usr/bin/python3
"""Module containing utilities to check the form values."""

from typing import Callable, Optional

from flask import flash
from loguru import logger
from werkzeug.local import LocalProxy
from werkzeug.utils import secure_filename

from brfast.config import params


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


def erroneous_field(request: LocalProxy, field_name: str,
                    verification: Callable[[str], bool], error_message: str
                    ) -> Optional[str]:
    """Check whether a field of a POST request is erroneous or not.

    This function also logs the error in the logger and as flash messages of
    Flask.

    Args:
        request: The request into which the parameter is checked.
        field_name: The name of the POST request field contaning the value.
        verification: A callable that checks the string value.
        error_message: The error message to display if the value is incorrect.

    Returns:
        An error message if something is wrong, None otherwise.
    """
    # Check that the field is in the form
    if field_name not in request.form:
        miss_err_mess = f'The field {field_name} is missing from the request.'
        flash(miss_err_mess, params.get('WebServer', 'flash_error_class'))
        logger.error(miss_err_mess)
        return miss_err_mess

    # Do the verifications on this field
    if not verification(request.form[field_name]):
        flash(error_message, params.get('WebServer', 'flash_error_class'))
        logger.error(error_message)
        return error_message

    # If everyting is fine, return None
    return None


def erroneous_post_file(request: LocalProxy, field_name: str,
                        expected_extension: Optional[str] = None
                        ) -> Optional[str]:
    """Check whether a file in a POST request is erroneous or not.

    This function also logs the error in the logger and as flash messages of
    Flask.

    Args:
        request: The request into which the file is checked.
        field_name: The name of the POST request field contaning the file.
        expected_extension: The expected extension of the file.

    Returns:
        An error message if an error was encountered or None otherwise.
    """
    clean_field_name = field_name.replace('-', ' ')

    # Check that the file is in the received POST request
    if not (field_name in request.files and request.files[field_name]):
        error_message = f'The {clean_field_name} file is missing.'
        flash(error_message, params.get('WebServer', 'flash_error_class'))
        logger.error(error_message)
        return error_message

    # Check that the extension of the file is allowed
    received_file = request.files[field_name]
    filename = secure_filename(received_file.filename)

    # The extension is not allowed
    if not allowed_extension(filename, expected_extension):
        error_message = (f'The file extension of the {clean_field_name} is not'
                         ' allowed.')
        if expected_extension:
            error_message += f' Expected the extension: {expected_extension}.'
        flash(error_message, params.get('WebServer', 'flash_error_class'))
        logger.error(error_message)
        return error_message

    # Everything is fine, no error then
    return None
