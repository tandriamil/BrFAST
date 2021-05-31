#!/usr/bin/python3
"""Module containing the dummy sensitivity and usability cost measures.

They simulate the lattice displayed in our FPSelect example.
"""

from brfast.data.attribute import AttributeSet
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure


SENSITIVITIES = {
    frozenset({}): 1.0,
    frozenset({1}): 0.3, frozenset({2}): 0.3, frozenset({3}): 0.25,
    frozenset({1, 2}): 0.15, frozenset({1, 3}): 0.25,
    frozenset({2, 3}): 0.20,
    frozenset({1, 2, 3}): 0.05
}

USABILITIES = {
    frozenset({}): 0,
    frozenset({1}): 10, frozenset({2}): 15, frozenset({3}): 15,
    frozenset({1, 2}): 20, frozenset({1, 3}): 17,
    frozenset({2, 3}): 25,
    frozenset({1, 2, 3}): 30
}

TOTAL_COST_FIELD = 'total_cost'


class DummySensitivity(SensitivityMeasure):
    """A dummy sensivity measure that takes the example of our paper."""

    def evaluate(self, attribute_set: AttributeSet) -> float:
        return SENSITIVITIES[frozenset(attribute_set.attribute_ids)]


class DummyUsabilityCostMeasure(UsabilityCostMeasure):
    """A dummy usability cost measure that takes the example of our paper."""

    def evaluate(self, attribute_set: AttributeSet) -> float:
        attribute_cost = USABILITIES[frozenset(attribute_set.attribute_ids)]
        return (attribute_cost, {TOTAL_COST_FIELD: attribute_cost})
