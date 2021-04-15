#!/usr/bin/python3
"""Module containing the usability cost measures inspired of FPSelect."""

from typing import Dict, Tuple

from brfast.data import Attribute, AttributeSet
from brfast.measures import UsabilityCostMeasure


class CostDimension:
    """Class reprensenting the cost dimensions."""

    MEMORY = 'memory'
    INSTABILITY = 'instability'
    TIME = 'time'
    ALL = {MEMORY, INSTABILITY, TIME}


class IncorrectWeightDimensions(Exception):
    """An exception when the dimensions are incorrect."""


class MemoryInstability(UsabilityCostMeasure):
    """Usability cost considering the memory and the instability of attributes.

    Similar to the usability cost measure used in the FPSelect paper but the
    collection time is missing here.
    """

    _expected_dimensions = {CostDimension.MEMORY, CostDimension.INSTABILITY}

    def __init__(self, size: Dict[Attribute, float],
                 instability: Dict[Attribute, float],
                 weights: Dict[Attribute, float]):
        """Initialize the cost measure that considers memory and instability.

        Args:
            size: A dictionary of the average size of the attributes.
            instability: A dictionary of the instability of the attributes.
            weights: The weights of the two dimensions: memory and instability.
        """
        # Initialize using the __init__ function of UsabilityCostMeasure
        super().__init__()

        # Set the variables used to compute the cost
        self._size = size
        self._instability = instability
        self._weights = weights

        # Check the keys of the weights
        received_dimensions = set(self._weights.keys())
        if received_dimensions != self._expected_dimensions:
            raise IncorrectWeightDimensions(
                f'The weight keys are {received_dimensions} but they should be'
                f' {self._expected_dimensions}.')

    def __repr__(self) -> str:
        """Provide a string representation of this usability cost measure.

        Returns:
            A string representation of this usability cost measure.
        """
        return f'{self.__class__.__name__}({self._weights})'

    def evaluate(self, attribute_set: AttributeSet) -> (float,
                                                        Dict[str, float]):
        """Measure the usability cost of an attribute set.

        The usability cost measure is required to be strictly increasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which cost is to be measured.

        Returns:
            A pair with the cost and its explanation. The cost is a numerical
            value whereas the explanation is a dictionary associating a cost
            dimension (str) to a cost value (float).
        """
        memory_cost, weighted_memory_cost = self._compute_memory_cost(
            attribute_set)
        instability_cost, weighted_instab_cost = (
            self._compute_instability_cost(attribute_set))
        total_cost = weighted_memory_cost + weighted_instab_cost
        cost_explanation = {
            CostDimension.MEMORY: memory_cost,
            f'weighted_{CostDimension.MEMORY}': weighted_memory_cost,
            CostDimension.INSTABILITY: instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': weighted_instab_cost
        }
        return (total_cost, cost_explanation)

    def _compute_memory_cost(self, attribute_set: AttributeSet
                             ) -> (float, float):
        """Compute the memory cost.

        Args:
            attribute_set: The attribute set to measure.

        Returns:
            A tuple of the memory cost and the weighted memory cost.
        """
        memory_cost = sum(self._size[attribute] for attribute in attribute_set)
        weighted_memory_cost = (memory_cost
                                * self._weights[CostDimension.MEMORY])
        return (memory_cost, weighted_memory_cost)

    def _compute_instability_cost(self, attribute_set: AttributeSet
                                  ) -> (float, float):
        """Compute the instability cost.

        Args:
            attribute_set: The attribute set to measure.

        Returns:
            A tuple of the instability cost and the weighted instability cost.
        """
        instability_cost = sum(self._instability[attribute]
                               for attribute in attribute_set)
        weighted_instability_cost = (
            instability_cost * self._weights[CostDimension.INSTABILITY])
        return (instability_cost, weighted_instability_cost)


class MemoryInstabilityTime(MemoryInstability):
    """Usability cost of the memory, the instability, and the collection time.

    This is the usability cost measure used in the FPSelect paper.
    """

    _expected_dimensions = {CostDimension.MEMORY, CostDimension.INSTABILITY,
                            CostDimension.TIME}

    def __init__(self, size: Dict[Attribute, float],
                 instability: Dict[Attribute, float],
                 time: Dict[Attribute, Tuple[float, bool]],
                 weights: Dict[Attribute, float]):
        """Initialize the cost measure (memory, instability, and col. time).

        Args:
            size: A dictionary of the average size of the attributes.
            instability: A dictionary of the instability of the attributes.
            time: A dictionary of pairs of the average collection time of the
                  attributes and a boolean specifying if the attribute is
                  asynchronous or not.
            weights: The weights of the two dimensions: memory and instability.
        """
        # Initialize using the __init__ function of UsabilityCostMeasure
        super().__init__(size, instability, weights)
        self._time = time

    def evaluate(self, attribute_set: AttributeSet) -> (float,
                                                        Dict[str, float]):
        """Measure the usability cost of an attribute set.

        The usability cost measure is required to be strictly increasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which cost is to be measured.

        Returns:
            A pair with the cost and its explanation. The cost is a numerical
            value whereas the explanation is a dictionary associating a cost
            dimension (str) to a cost value (float).
        """
        memory_cost, weighted_memory_cost = self._compute_memory_cost(
            attribute_set)
        instability_cost, weighted_instab_cost = (
            self._compute_instability_cost(attribute_set))
        col_time_cost, weighted_col_time_cost = self._compute_time_cost(
            attribute_set)
        total_cost = sum((weighted_memory_cost, weighted_instab_cost,
                          weighted_col_time_cost))
        cost_explanation = {
            CostDimension.MEMORY: memory_cost,
            f'weighted_{CostDimension.MEMORY}': weighted_memory_cost,
            CostDimension.INSTABILITY: instability_cost,
            f'weighted_{CostDimension.INSTABILITY}': weighted_instab_cost,
            CostDimension.TIME: col_time_cost,
            f'weighted_{CostDimension.TIME}': weighted_col_time_cost
        }
        return (total_cost, cost_explanation)

    def _compute_time_cost(self, attribute_set: AttributeSet
                           ) -> (float, float):
        """Compute the collection time cost.

        Args:
            attribute_set: The attribute set to measure.

        Returns:
            A tuple of the col. time cost and the weighted col. time cost.
        """
        sequential_attrs_col_time = 0.0  # The col. time of the sequential att.
        max_asynchronous_col_time = 0.0  # The col. time of the longest async.
        for attribute in attribute_set:
            av_col_time, is_asynchronous = self._time[attribute]
            if is_asynchronous:
                if av_col_time > max_asynchronous_col_time:
                    max_asynchronous_col_time = av_col_time
            else:
                sequential_attrs_col_time += av_col_time
        collection_time_cost = max(sequential_attrs_col_time,
                                   max_asynchronous_col_time)
        weighted_collection_time_cost = (
            collection_time_cost * self._weights[CostDimension.TIME])
        return (collection_time_cost, weighted_collection_time_cost)
