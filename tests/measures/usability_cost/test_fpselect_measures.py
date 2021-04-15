#!/usr/bin/python3
"""Test module of the usability cost measures used in the FPSelect paper."""

import unittest
from copy import copy

from brfast.data import Attribute, AttributeSet
from brfast.measures.usability_cost.fpselect import (
    IncorrectWeightDimensions, MemoryInstability, MemoryInstabilityTime,
    CostDimension)

from tests.data import ATTRIBUTES

SIZES = {ATTRIBUTES[0]: 52.25, ATTRIBUTES[1]: 42.56, ATTRIBUTES[2]: 1}
INSTABILITIES = {ATTRIBUTES[0]: 0.05, ATTRIBUTES[1]: 0.15, ATTRIBUTES[2]: 0.0}
COLLECTION_TIMES = {ATTRIBUTES[0]: (0.05, False),
                    ATTRIBUTES[1]: (0.0001, False),
                    ATTRIBUTES[2]: (0.003, False)}
WEIGHTS = {CostDimension.MEMORY: 1, CostDimension.INSTABILITY: 100,
           CostDimension.TIME: 1000}


class TestMemoryInstability(unittest.TestCase):

    def setUp(self):
        weights_copy = copy(WEIGHTS)
        del weights_copy[CostDimension.TIME]
        self._memory_instability_measure = MemoryInstability(
            SIZES, INSTABILITIES, weights_copy)

    def test_repr(self):
        self.assertIsInstance(str(self._memory_instability_measure), str)

    def test_incorrect_weight_dimensions(self):
        # One additional weight dimension
        with self.assertRaises(IncorrectWeightDimensions):
            memory_instability = MemoryInstability(SIZES, INSTABILITIES,
                                                   WEIGHTS)

        # One missing weight dimension
        right_dimensions = copy(WEIGHTS)
        del right_dimensions[CostDimension.TIME]
        for dimension, weight_value in right_dimensions.items():
            single_dimension = {dimension: weight_value}
            with self.assertRaises(IncorrectWeightDimensions):
                memory_instability = MemoryInstability(SIZES, INSTABILITIES,
                                                       single_dimension)

        # No weight at all
        with self.assertRaises(IncorrectWeightDimensions):
            memory_instability = MemoryInstability(SIZES, INSTABILITIES,
                                                   dict())

    def test_evaluate_unknown_attribute_id(self):
        attributes_with_unknown = ATTRIBUTES + [Attribute(-1, 'unknown')]
        with self.assertRaises(KeyError):
            empty_attr_cost, empty_attr_cost_explanation = (
                 self._memory_instability_measure.evaluate(
                     attributes_with_unknown))

    def test_evaluate_empty_attribute_set(self):
        empty_attr_cost, empty_attr_cost_explanation = (
             self._memory_instability_measure.evaluate(AttributeSet()))
        self.assertEqual(empty_attr_cost, 0.0)
        for cost_value in empty_attr_cost_explanation.values():
            self.assertEqual(cost_value, 0.0)

    def test_evaluate(self):
        attribute_set = AttributeSet(ATTRIBUTES)
        cost, cost_explanation = self._memory_instability_measure.evaluate(
            attribute_set)
        expected_memory_cost = sum(SIZES.values())
        expected_weighted_memory_cost = (
            expected_memory_cost * WEIGHTS[CostDimension.MEMORY])
        expected_instability_cost = sum(INSTABILITIES.values())
        expected_weighted_instability_cost = (
            expected_instability_cost * WEIGHTS[CostDimension.INSTABILITY])
        expected_cost = (expected_weighted_memory_cost
                         + expected_weighted_instability_cost)
        expected_cost_explanation = {
            CostDimension.MEMORY: expected_memory_cost,
            f'weighted_{CostDimension.MEMORY}': expected_weighted_memory_cost,
            CostDimension.INSTABILITY: expected_instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': (
                expected_weighted_instability_cost)
        }
        self.assertEqual(cost, expected_cost)
        self.assertDictEqual(cost_explanation, expected_cost_explanation)


class TestMemoryInstabilityTime(unittest.TestCase):

    def setUp(self):
        self._memory_instability_time_measure = MemoryInstabilityTime(
            SIZES, INSTABILITIES, COLLECTION_TIMES, WEIGHTS)

    def test_evaluate_unknown_attribute_id(self):
        attributes_with_unknown = ATTRIBUTES + [Attribute(-1, 'unknown')]
        with self.assertRaises(KeyError):
            empty_attr_cost, empty_attr_cost_explanation = (
                 self._memory_instability_time_measure.evaluate(
                     attributes_with_unknown))

    def test_evaluate_empty_attribute_set(self):
        empty_attr_cost, empty_attr_cost_explanation = (
             self._memory_instability_time_measure.evaluate(AttributeSet()))
        self.assertEqual(empty_attr_cost, 0.0)
        for cost_value in empty_attr_cost_explanation.values():
            self.assertEqual(cost_value, 0.0)

    def test_evaluate_sequential_only(self):
        attribute_set = AttributeSet(ATTRIBUTES)
        cost, cost_explanation = (
            self._memory_instability_time_measure.evaluate(attribute_set))
        expected_memory_cost = sum(SIZES.values())
        expected_weighted_memory_cost = (
            expected_memory_cost * WEIGHTS[CostDimension.MEMORY])
        expected_instability_cost = sum(INSTABILITIES.values())
        expected_weighted_instability_cost = (
            expected_instability_cost * WEIGHTS[CostDimension.INSTABILITY])
        # Sequential test: there are only sequential attributes.
        expected_time_cost = sum(
            avg_col_time for avg_col_time, _ in COLLECTION_TIMES.values())
        expected_weighted_time_cost = (
            expected_time_cost * WEIGHTS[CostDimension.TIME])
        expected_cost = sum((expected_weighted_memory_cost,
                             expected_weighted_instability_cost,
                             expected_weighted_time_cost))
        expected_cost_explanation = {
            CostDimension.MEMORY: expected_memory_cost,
            f'weighted_{CostDimension.MEMORY}': expected_weighted_memory_cost,
            CostDimension.INSTABILITY: expected_instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': (
                expected_weighted_instability_cost),
            CostDimension.TIME: expected_time_cost,
            f'weighted_{CostDimension.TIME}': expected_weighted_time_cost
        }
        self.assertEqual(cost, expected_cost)
        self.assertDictEqual(cost_explanation, expected_cost_explanation)

    def test_evaluate_sequential_asynchronous_mix_seq_max(self):
        # Sequential / asynchronous mix, but the total collection time of the
        # sequential attributes is higher than the higher asynchronous time.
        collection_times_mix_seq_max = {
            ATTRIBUTES[0]: (0.05, False), ATTRIBUTES[1]: (0.02, False),
            ATTRIBUTES[2]: (0.06, True)
        }
        memory_instability_time_measure = MemoryInstabilityTime(
            SIZES, INSTABILITIES, collection_times_mix_seq_max, WEIGHTS)
        attribute_set = AttributeSet(ATTRIBUTES)
        cost, cost_explanation = memory_instability_time_measure.evaluate(
            attribute_set)
        expected_memory_cost = sum(SIZES.values())
        expected_weighted_memory_cost = (
            expected_memory_cost * WEIGHTS[CostDimension.MEMORY])
        expected_instability_cost = sum(INSTABILITIES.values())
        expected_weighted_instability_cost = (
            expected_instability_cost * WEIGHTS[CostDimension.INSTABILITY])
        expected_time_cost = sum(
            avg_col_time
            for avg_col_time, is_asyn in collection_times_mix_seq_max.values()
            if not is_asyn)
        expected_weighted_time_cost = (
            expected_time_cost * WEIGHTS[CostDimension.TIME])
        expected_cost = sum((expected_weighted_memory_cost,
                             expected_weighted_instability_cost,
                             expected_weighted_time_cost))
        expected_cost_explanation = {
            CostDimension.MEMORY: expected_memory_cost,
            f'weighted_{CostDimension.MEMORY}': expected_weighted_memory_cost,
            CostDimension.INSTABILITY: expected_instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': (
                expected_weighted_instability_cost),
            CostDimension.TIME: expected_time_cost,
            f'weighted_{CostDimension.TIME}': expected_weighted_time_cost
        }
        self.assertEqual(cost, expected_cost)
        self.assertDictEqual(cost_explanation, expected_cost_explanation)

    def test_evaluate_sequential_asynchronous_mix_async_max(self):
        # Sequential / asynchronous mix, but the collection time of the
        # single asynchronous attribute is higher than the total collection
        # time of the sequential attributes.
        collection_times_mix_async_max = {
            ATTRIBUTES[0]: (0.05, False), ATTRIBUTES[1]: (0.02, False),
            ATTRIBUTES[2]: (0.09, True)
        }
        memory_instability_time_measure = MemoryInstabilityTime(
            SIZES, INSTABILITIES, collection_times_mix_async_max, WEIGHTS)
        attribute_set = AttributeSet(ATTRIBUTES)
        cost, cost_explanation = memory_instability_time_measure.evaluate(
            attribute_set)
        expected_memory_cost = sum(SIZES.values())
        expected_weighted_memory_cost = (
            expected_memory_cost * WEIGHTS[CostDimension.MEMORY])
        expected_instability_cost = sum(INSTABILITIES.values())
        expected_weighted_instability_cost = (
            expected_instability_cost * WEIGHTS[CostDimension.INSTABILITY])
        expected_time_cost = collection_times_mix_async_max[ATTRIBUTES[2]][0]
        expected_weighted_time_cost = (
            expected_time_cost * WEIGHTS[CostDimension.TIME])
        expected_cost = sum((expected_weighted_memory_cost,
                             expected_weighted_instability_cost,
                             expected_weighted_time_cost))
        expected_cost_explanation = {
            CostDimension.MEMORY: expected_memory_cost,
            f'weighted_{CostDimension.MEMORY}': expected_weighted_memory_cost,
            CostDimension.INSTABILITY: expected_instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': (
                expected_weighted_instability_cost),
            CostDimension.TIME: expected_time_cost,
            f'weighted_{CostDimension.TIME}': expected_weighted_time_cost
        }
        self.assertEqual(cost, expected_cost)
        self.assertDictEqual(cost_explanation, expected_cost_explanation)

    def test_evaluate_sequential_asynchronous_only(self):
        # Asynchronous attributes only.
        collection_times_async_only = {
            ATTRIBUTES[0]: (0.05, True), ATTRIBUTES[1]: (0.08, True),
            ATTRIBUTES[2]: (0.03, True)
        }
        memory_instability_time_measure = MemoryInstabilityTime(
            SIZES, INSTABILITIES, collection_times_async_only, WEIGHTS)
        attribute_set = AttributeSet(ATTRIBUTES)
        cost, cost_explanation = memory_instability_time_measure.evaluate(
            attribute_set)
        expected_memory_cost = sum(SIZES.values())
        expected_weighted_memory_cost = (
            expected_memory_cost * WEIGHTS[CostDimension.MEMORY])
        expected_instability_cost = sum(INSTABILITIES.values())
        expected_weighted_instability_cost = (
            expected_instability_cost * WEIGHTS[CostDimension.INSTABILITY])
        expected_time_cost = max(
            avg_col_time
            for avg_col_time, is_async in collection_times_async_only.values())
        expected_weighted_time_cost = (
            expected_time_cost * WEIGHTS[CostDimension.TIME])
        expected_cost = sum((expected_weighted_memory_cost,
                             expected_weighted_instability_cost,
                             expected_weighted_time_cost))
        expected_cost_explanation = {
            CostDimension.MEMORY: expected_memory_cost,
            f'weighted_{CostDimension.MEMORY}': expected_weighted_memory_cost,
            CostDimension.INSTABILITY: expected_instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': (
                expected_weighted_instability_cost),
            CostDimension.TIME: expected_time_cost,
            f'weighted_{CostDimension.TIME}': expected_weighted_time_cost
        }
        self.assertEqual(cost, expected_cost)
        self.assertDictEqual(cost_explanation, expected_cost_explanation)


if __name__ == '__main__':
    unittest.main()
