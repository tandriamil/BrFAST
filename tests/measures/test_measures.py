#!/usr/bin/python3
"""Test test module of the abtract classes for the measures."""

import unittest

from brfast.data import AttributeSet
from brfast.measures import SensitivityMeasure, UsabilityCostMeasure


class TestSensitivityMeasure(unittest.TestCase):

    def test_evaluate_abstract(self):
        sensitivity_measure = SensitivityMeasure()
        with self.assertRaises(NotImplementedError):
            sensitivity_measure.evaluate(AttributeSet())


class TestUsabilityCostMeasure(unittest.TestCase):

    def test_evaluate_abstract(self):
        usability_cost_measure = UsabilityCostMeasure()
        with self.assertRaises(NotImplementedError):
            usability_cost_measure.evaluate(AttributeSet())


if __name__ == '__main__':
    unittest.main()
