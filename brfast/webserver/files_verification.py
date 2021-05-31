#!/usr/bin/python3
"""Module to check the content of the files received by the web application."""

from typing import Optional

from brfast.exploration import ExplorationParameters, TraceData

SEP = '/'


def trace_file_errors(trace_dict: dict) -> Optional[str]:
    """Verify the trace file decoded from json to a dictionary.

    Args:
        trace_dict: The dictionary obtained from the trace file.

    Returns:
        An error message if an error was encountered.
    """
    try:
        assert isinstance(trace_dict[TraceData.PARAMETERS],
                          dict), TraceData.PARAMETERS
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.METHOD], str), (
                TraceData.PARAMETERS + SEP + ExplorationParameters.METHOD)
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.SENSITIVITY_MEASURE], str), (
                TraceData.PARAMETERS + SEP
                + ExplorationParameters.SENSITIVITY_MEASURE)
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.USABILITY_COST_MEASURE], str), (
                TraceData.PARAMETERS + SEP
                + ExplorationParameters.USABILITY_COST_MEASURE)
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.DATASET], str), (
                TraceData.PARAMETERS + SEP + ExplorationParameters.DATASET)
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.SENSITIVITY_THRESHOLD], float), (
                TraceData.PARAMETERS + SEP
                + ExplorationParameters.SENSITIVITY_THRESHOLD)
        assert isinstance(trace_dict[TraceData.PARAMETERS][
            ExplorationParameters.ANALYSIS_ENGINE], str), (
                TraceData.PARAMETERS + SEP
                + ExplorationParameters.ANALYSIS_ENGINE)

        assert isinstance(trace_dict[TraceData.ATTRIBUTES], dict), (
            TraceData.ATTRIBUTES)

        assert isinstance(trace_dict[TraceData.RESULT], dict), TraceData.RESULT
        assert isinstance(trace_dict[TraceData.RESULT][TraceData.SOLUTION],
                          list), TraceData.RESULT + SEP + TraceData.SOLUTION
        assert isinstance(trace_dict[TraceData.RESULT][
            TraceData.SATISFYING_ATTRIBUTES], list), (
                TraceData.RESULT + SEP + TraceData.SATISFYING_ATTRIBUTES)
        assert isinstance(trace_dict[TraceData.RESULT][TraceData.START_TIME],
                          str), TraceData.RESULT + SEP + TraceData.START_TIME

        explored_attribute_sets = trace_dict[TraceData.EXPLORATION]
        assert isinstance(explored_attribute_sets, list)
        for expl_attr_set in explored_attribute_sets:
            assert isinstance(expl_attr_set[TraceData.ATTRIBUTES], list), (
                TraceData.EXPLORATION + SEP + TraceData.ATTRIBUTES)
            assert isinstance(expl_attr_set[TraceData.SENSITIVITY], float), (
                TraceData.EXPLORATION + SEP + TraceData.SENSITIVITY)
            assert isinstance(float(expl_attr_set[TraceData.USABILITY_COST]),
                              float), (TraceData.EXPLORATION + SEP
                                       + TraceData.USABILITY_COST)
            assert isinstance(expl_attr_set[TraceData.COST_EXPLANATION],
                              dict), (TraceData.EXPLORATION + SEP
                                      + TraceData.COST_EXPLANATION)
            assert isinstance(expl_attr_set[TraceData.STATE], int), (
                TraceData.EXPLORATION + SEP + TraceData.STATE)
            assert isinstance(expl_attr_set[TraceData.ATTRIBUTE_SET_ID],
                              int), (TraceData.EXPLORATION + SEP
                                     + TraceData.ATTRIBUTE_SET_ID)
    except KeyError as key_error:
        return f'The {key_error.args[0]} field is missing from the trace file.'
    except ValueError:
        return (f'The {TraceData.USABILITY_COST} field should be either an '
                'int or otherwise a float.')
    except AssertionError as erroneous_field:
        return f'The {erroneous_field} field does not have the right type.'

    return None
