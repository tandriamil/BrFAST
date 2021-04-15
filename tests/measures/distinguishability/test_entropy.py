#!/usr/bin/python3
"""Test module of the brfast.measures.distinguishability.entropy module."""

import unittest
from math import log2

from brfast.data import Attribute, AttributeSet
from brfast.measures.distinguishability.entropy import attribute_set_entropy

from tests.data import ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset


class TestAttributeSetEntropy(unittest.TestCase):

    def setUp(self):
        self._dummy_dataset = DummyCleanDataset()

    def test_empty_dataset(self):
        empty_dataset = DummyEmptyDataset()
        attribute_set = AttributeSet()
        self.assertEqual(0.0,
                         attribute_set_entropy(empty_dataset, attribute_set))

    def test_empty_attribute_set(self):
        attribute_set = AttributeSet()
        with self.assertRaises(ValueError):
            attribute_set_entropy(self._dummy_dataset, attribute_set)

    def test_unexistent_attribute(self):
        attribute_set = AttributeSet(ATTRIBUTES)
        attribute_set.add(Attribute(42, 'missing_from_dataset'))
        with self.assertRaises(KeyError):
            attribute_set_entropy(self._dummy_dataset, attribute_set)

    def test_always_the_same_value(self):
        attribute_set = AttributeSet([ATTRIBUTES[2]])
        self.assertEqual(0.0, attribute_set_entropy(self._dummy_dataset,
                                                    attribute_set))

    def test_in_between_entropy(self):
        attribute_set = AttributeSet([ATTRIBUTES[0]])
        expected_entropy = -1 * ((1/5)*log2(1/5) + (2/5)*log2(2/5)
                                 + (2/5)*log2(2/5))
        self.assertAlmostEqual(expected_entropy,
                               attribute_set_entropy(self._dummy_dataset,
                                                     attribute_set))

    def test_unique_values(self):
        attribute_set = AttributeSet([ATTRIBUTES[1]])
        expected_entropy = log2(len(self._dummy_dataset.dataframe))
        self.assertAlmostEqual(expected_entropy,
                               attribute_set_entropy(self._dummy_dataset,
                                                     attribute_set))


if __name__ == '__main__':
    unittest.main()
