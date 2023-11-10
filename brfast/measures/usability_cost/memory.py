#!/usr/bin/python3
"""Measures of the average size of the attributes of a fingerprint dataset."""

import importlib
from math import ceil
from multiprocessing import Pool
from os import cpu_count
from typing import Any, Dict, List

from loguru import logger
from sortedcontainers import SortedDict

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.measures import Analysis

pd = importlib.import_module(params.get('DataAnalysis', 'engine'))


class AverageFingerprintSize(Analysis):
    """Measure the average fingerprint size of the attributes of a dataset."""

    def execute(self):
        """Measure the average fingerprint size of the attributes."""
        if params.getboolean('Multiprocessing', 'measures'):
            logger.debug('Measuring the average fingerprint size using '
                         'multiprocessing...')
            self._execute_using_multiprocessing()
        else:
            logger.debug(
                'Measuring the average fingerprint on a single process...')
            self._result = _compute_attribute_avg_size(
                self._dataset.dataframe, self._dataset.candidate_attributes)

    def _execute_using_multiprocessing(self):
        """Measure the average fingerprint size using multiprocessing."""
        # The list of pairs of (Attribute, attribute average size)
        attributes_avg_size = SortedDict()

        # Infer the number of cores to use
        free_cores = params.getint('Multiprocessing', 'free_cores')
        nb_cores = max(cpu_count() - free_cores, 1)
        nb_attributes = len(self._dataset.candidate_attributes)
        attributes_per_core = int(ceil(nb_attributes/nb_cores))
        logger.debug(f'Sharing {nb_attributes} attributes over '
                     f'{nb_cores}(+{free_cores}) cores, hence '
                     f'{attributes_per_core} attributes per core.')

        def update_attributes_average_size(attrs_size: Dict[Attribute, float]):
            """Update the complete dictionary attributes_avg_size.

            Args:
                attrs_size: The dictionary containing the subset of the results
                            computed by a process.

            Note: This is executed by the main thread and does not pose any
                  concurrency or synchronization problem.
            """
            for attribute, attribute_average_size in attrs_size.items():
                attributes_avg_size[attribute] = attribute_average_size

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
                    _compute_attribute_avg_size,
                    args=(self._dataset.dataframe, attributes_subset),
                    callback=update_attributes_average_size)
                async_results.append(async_result)

            # Wait for all the processes to finish (otherwise we would exit
            # before collecting their result)
            for async_result in async_results:
                async_result.wait()

        self._result = attributes_avg_size

    def _from_dict_to_row_list(self) -> List[List[Any]]:
        """Give the representation of the csv result as a list of rows.

        Returns:
            A list of rows, each row being a list of values to store. The first
            row should contain the headers.
        """
        row_list = [['attribute', 'average_size']]  # The header
        for attribute, average_size in self._result.items():
            row_list.append([attribute.name, average_size])
        return row_list


def _compute_attribute_avg_size(dataframe: pd.DataFrame,
                                attributes: AttributeSet
                                ) -> Dict[Attribute, float]:
    """Compute the average size of each attribute (passed to each process).

    Args:
        dataframe: The dataframe used to compute the average size.
        attributes: The attributes for which to compute the average size.

    Raises:
        KeyError: One of the attribute is not in the dataset.

    Returns:
        A dictionary of the subset of the attributes and their average size.
    """
    attributes_avg_size = {}
    for attribute in attributes:
        # 1. Project the dataframe on the attribute (get Series)
        # 2. Map the values of this attribute to their length
        # 3. Obtain the average of the sizes
        average_size = (dataframe[attribute.name]
                        .apply(lambda value: len(str(value)))
                        .mean())
        attributes_avg_size[attribute] = average_size
    return attributes_avg_size
