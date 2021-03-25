#!/usr/bin/python3
"""Test module of the brfast.utils.sequences module."""

import unittest

from brfast.utils.sequences import sort_dict_by_value


class TestSortDictByValue(unittest.TestCase):

    def test_sort_dict_by_value_empty(self):
        self.assertEqual([], sort_dict_by_value({}))

    def test_sort_dict_by_value_ascending(self):
        self.assertEqual([(1, '1'), (2, '2'), (3, '3'), (4, '4')],
                         sort_dict_by_value({3: '3', 1: '1', 4: '4', 2: '2'}))

    def test_sort_dict_by_value_descending(self):
        self.assertEqual([(4, '4'), (3, '3'), (2, '2'), (1, '1')],
                         sort_dict_by_value({3: '3', 1: '1', 4: '4', 2: '2'},
                                            reverse=True))


if __name__ == '__main__':
    unittest.main()
