#!/usr/bin/python3
"""Init file of the tests.exploration module."""

from typing import Any, Dict

from brfast.data import AttributeSet
from brfast.exploration import (
    Exploration, ExplorationNotRun, ExplorationParameters,
    SensitivityThresholdUnreachable, State, TraceData)

from tests.data import ATTRIBUTES
from tests.measures import SENSITIVITIES, TOTAL_COST_FIELD, USABILITIES

DUMMY_PARAMETER_FIELD = 'dummy_parameter'
SENSITIVITY_THRESHOLD = 0.15
TRACE_FILENAME = 'tested_trace.json'
MODIN_ANALYSIS_ENGINES = ['modin.pandas[dask]', 'modin.pandas[ray]']


class DummyExploration(Exploration):
    """A dummy exploration class that only set the variables."""

    def _search_for_solution(self):
        # Set the final solution found
        self._solution = AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]})

        # Update the set of the attribute sets that satisfy the sensitivity
        self._satisfying_attribute_sets = {
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}),
            AttributeSet(ATTRIBUTES)
        }

        # Update the list of the explored attributes
        self._explored_attr_sets = [
            {
                TraceData.TIME: 5,
                TraceData.ATTRIBUTES: [1, 2, 3],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({1, 2, 3})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({1, 2, 3})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({1, 2, 3})]},
                TraceData.STATE: State.SATISFYING
            },
            {
                TraceData.TIME: 10,
                TraceData.ATTRIBUTES: [1],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({1})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({1})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({1})]},
                TraceData.STATE: State.EXPLORED
            },
            {
                TraceData.TIME: 15,
                TraceData.ATTRIBUTES: [2],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({2})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({2})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({2})]},
                TraceData.STATE: State.EXPLORED
            },
            {
                TraceData.TIME: 20,
                TraceData.ATTRIBUTES: [3],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({3})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({3})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({3})]},
                TraceData.STATE: State.EXPLORED
            },
            {
                TraceData.TIME: 30,
                TraceData.ATTRIBUTES: [1, 2],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({1, 2})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({1, 2})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({1, 2})]},
                TraceData.STATE: State.SATISFYING
            },
            {
                TraceData.TIME: 40,
                TraceData.ATTRIBUTES: [1, 3],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({1, 3})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({1, 3})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({1, 3})]},
                TraceData.STATE: State.EXPLORED
            },
            {
                TraceData.TIME: 50,
                TraceData.ATTRIBUTES: [2, 3],
                TraceData.SENSITIVITY: SENSITIVITIES[frozenset({2, 3})],
                TraceData.USABILITY_COST: USABILITIES[frozenset({2, 3})],
                TraceData.COST_EXPLANATION:  {
                    TOTAL_COST_FIELD: USABILITIES[frozenset({2, 3})]},
                TraceData.STATE: State.PRUNED
            }
        ]

    @property
    def parameters(self) -> Dict[str, Any]:
        default_parameters = self._default_parameters()
        default_parameters[DUMMY_PARAMETER_FIELD] = 42
        return default_parameters
