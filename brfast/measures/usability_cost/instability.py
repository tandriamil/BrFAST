#!/usr/bin/python3
"""Measures of the instability of the attribues of a fingerprint dataset."""

from math import ceil
from multiprocessing import Pool
from os import cpu_count
from typing import Any, Dict, List

from loguru import logger
from pandas.core.groupby.generic import DataFrameGroupBy

from brfast.config import ANALYSIS_ENGINES, params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import MetadataField
from brfast.measures import Analysis


class ProportionOfChanges(Analysis):
    """Measure the average instability of the attributes of a dataset."""

    def execute(self):
        """Measure the average instability of the attributes.

        If there are no consecutive fingerprints, the instability of each
        attribute is of 0.0 (i.e., no changes have been observed).

        Note:
            This measure does not use modin due to a bug where no comparisons
            are retrieved.
        """
        dataframe = self._dataset.dataframe

        # Force to use pandas.DataFrame due to a bug
        if params.get('DataAnalysis', 'engine') == ANALYSIS_ENGINES[1]:
            dataframe = dataframe._to_pandas()

        # 1. Group by the browser id (no sort for performances, no group key to
        #    not add a column with the group key)
        # 2. Sort by the time of collection for each group (give a DataFrame)
        # 3. Regroup by the browser id, here each group has the fingerprints
        #    sorted by the time of collection
        grouped_by_browser = (
            dataframe
            .groupby(MetadataField.BROWSER_ID, sort=False, group_keys=False)
            .apply(lambda group_df: group_df.sort_values(
                MetadataField.TIME_OF_COLLECT))
            .groupby(MetadataField.BROWSER_ID, sort=False, group_keys=False))

        if params.getboolean('Multiprocessing', 'measures'):
            logger.debug('Measuring the instability size using '
                         'multiprocessing...')
            self._execute_using_multiprocessing(grouped_by_browser)
        else:
            logger.debug('Measuring the instability on a single process...')
            self._result = _compute_attributes_instability(
                grouped_by_browser, self._dataset.candidate_attributes)

    def _execute_using_multiprocessing(self,
                                       grouped_by_browser: DataFrameGroupBy):
        """Measure the average fingerprint size using multiprocessing.

        Args:
            grouped_by_browser: The group by dataframe containing the
                                fingerprints of each browser.
        """
        attributes_instability = {}

        # Infer the number of cores to use
        free_cores = params.getint('Multiprocessing', 'free_cores')
        nb_cores = max(cpu_count() - free_cores, 1)
        nb_attributes = len(self._dataset.candidate_attributes)
        attributes_per_core = int(ceil(nb_attributes/nb_cores))
        logger.debug(f'Sharing {nb_attributes} attributes over '
                     f'{nb_cores}(+{free_cores}) cores, hence '
                     f'{attributes_per_core} attributes per core.')

        def update_attributes_instability(attrs_inst: Dict[Attribute, float]):
            """Update the complete dictionary attributes_instability.

            Args:
                attrs_inst: The dictionary containing the subset of the results
                            computed by a process.

            Note: This is executed by the main thread and does not pose any
                  concurrency or synchronization problem.
            """
            for attribute, attribute_instability in attrs_inst.items():
                attributes_instability[attribute] = attribute_instability

        # Spawn a number of processes equal to the number of cores
        attributes_list = list(self._dataset.candidate_attributes)
        async_results = []
        with Pool(processes=nb_cores) as pool:
            for process_id in range(nb_cores):
                # Generate the candidate attributes for this process
                start_id = process_id * attributes_per_core
                end_id = (process_id + 1) * attributes_per_core
                attributes_subset = AttributeSet(
                    attributes_list[start_id:end_id])

                async_result = pool.apply_async(
                    _compute_attributes_instability,
                    args=(grouped_by_browser, attributes_subset),
                    callback=update_attributes_instability)
                async_results.append(async_result)

            # Wait for all the processes to finish (otherwise we would exit
            # before collecting their result)
            for async_result in async_results:
                async_result.wait()

        self._result = attributes_instability

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = [['attribute', 'proportion_of_changes']]  # The header
        for attribute, instability in self._result.items():
            row_list.append([attribute.name, instability])
        return row_list


def _compute_attributes_instability(grouped_by_browser: DataFrameGroupBy,
                                    attributes: AttributeSet) -> Dict[
                                        Attribute, float]:
    """Compute the instability of each attribute (passed to each process).

    Args:
        grouped_by_browser: The group by dataframe containing the fingerprints
                            of each browser.
        attributes: The attributes for which to compute the instability.

    Raises:
        KeyError: There are fingerprints and one of the attribute is not in the
                  dataset.

    Returns:
        A dictionary of the subset of the attributes and their instability.
    """
    attributes_instability = {}

    # For each attribute, we compute its instability as the proportion of
    # value changes over the number of comparisons (= pairs of consecutive
    # fingerprints)
    for attribute in attributes:
        comparisons, changes = 0, 0

        # Each group contains the consecutive fingerprints of a browser
        for _, fingerprints_df in grouped_by_browser:

            # Get the Series of the values of the attribute
            attribute_values = fingerprints_df[attribute.name]

            # For each value and the next one. For three values v1, v2, v3,
            # we then compare (v1, v2) and (v2, v3)
            for value, next_value in zip(attribute_values,
                                         attribute_values[1:]):
                comparisons += 1
                if value != next_value:
                    changes += 1

        # If there are no comparisons (i.e., no consecutive fingerprints)
        if comparisons == 0:
            attributes_instability[attribute] = 0.0
        else:
            attributes_instability[attribute] = changes / comparisons

    return attributes_instability
