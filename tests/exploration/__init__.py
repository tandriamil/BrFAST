#!/usr/bin/python3
"""Init file."""

from typing import Any, Dict

from brfast.data.attribute import AttributeSet
from brfast.exploration import Exploration, State, TraceData
from tests.data import ATTRIBUTES
from tests.measures import SENSITIVITIES, TOTAL_COST_FIELD, USABILITIES

DUMMY_PARAMETER = {'dummy_parameter': 42}
SENSITIVITY_THRESHOLD = 0.15
TRACE_FILENAME = 'tested_trace.json'
MODIN_ANALYSIS_ENGINES = ['modin.pandas[dask]', 'modin.pandas[ray]']


class DummyExploration(Exploration):
    """A dummy exploration class that only set the variables."""

    EXPLORED_ATTRIBUTE_SETS = [
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

    def _search_for_solution(self):
        # Set the final solution found
        self._update_solution(AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}))

        # Update the set of the attribute sets that satisfy the sensitivity
        self._add_satisfying_attribute_set(
            AttributeSet({ATTRIBUTES[0], ATTRIBUTES[1]}))
        self._add_satisfying_attribute_set(AttributeSet(ATTRIBUTES))

        # Update the list of the explored attributes. We ignore the first
        # attribute set composed of all the attributes which is automatically
        # added when checking that the sensitivity threshold is reachable
        for explored_attribute_set in self.EXPLORED_ATTRIBUTE_SETS[1:]:
            self._add_explored_attribute_set(explored_attribute_set)

    @property
    def parameters(self) -> Dict[str, Any]:
        default_parameters = self._default_parameters()
        for additional_parameter, value in DUMMY_PARAMETER.items():
            default_parameters[additional_parameter] = value
        return default_parameters
