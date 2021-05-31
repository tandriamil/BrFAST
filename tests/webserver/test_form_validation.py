#!/usr/bin/python3
"""Test module of the brfast.utils.form_validation module."""

import unittest
from itertools import product

from brfast.webserver.form_validation import (
    allowed_extension, ALLOWED_EXTENSIONS)


FILENAME_BASE = 'file.%s'
FILENAME_WITHOUT_EXTENSION = 'filename_without_extension'
RANDOM_UNALLOWED_EXTENSIONS = {'php', 'png', 'txt'}


class TestAllowedExtension(unittest.TestCase):

    def test_without_extension(self):
        filename = FILENAME_WITHOUT_EXTENSION
        self.assertFalse(allowed_extension(filename))
        for allowed_ext in ALLOWED_EXTENSIONS:
            self.assertFalse(allowed_extension(filename,
                                               expected_extension=allowed_ext))

    def test_without_expected_extension(self):
        for allowed_ext in ALLOWED_EXTENSIONS:
            self.assertTrue(allowed_extension(FILENAME_BASE % allowed_ext))
        for unallowed_ext in RANDOM_UNALLOWED_EXTENSIONS:
            self.assertFalse(allowed_extension(FILENAME_BASE % unallowed_ext))

    def test_with_expected_extension(self):
        for allowed_ext, unallowed_ext in product(ALLOWED_EXTENSIONS,
                                                  RANDOM_UNALLOWED_EXTENSIONS):
            self.assertTrue(allowed_extension(FILENAME_BASE % allowed_ext,
                                              expected_extension=allowed_ext))
            self.assertFalse(allowed_extension(FILENAME_BASE % unallowed_ext,
                                               expected_extension=allowed_ext))
        for allowed_ext, unallowed_ext in product(RANDOM_UNALLOWED_EXTENSIONS,
                                                  ALLOWED_EXTENSIONS):
            self.assertTrue(allowed_extension(FILENAME_BASE % allowed_ext,
                                              expected_extension=allowed_ext))
            self.assertFalse(allowed_extension(FILENAME_BASE % unallowed_ext,
                                               expected_extension=allowed_ext))


if __name__ == '__main__':
    unittest.main()
