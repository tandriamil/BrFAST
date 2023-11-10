#!/usr/bin/python3
"""Init file."""

import csv
from pathlib import Path
from typing import Dict

from loguru import logger

from brfast.data.attribute import Attribute, AttributeSet


def read_csv_analysis_as_dict(csv_file_path: Path,
                              candidate_attributes: AttributeSet
                              ) -> Dict[Attribute, float]:
    """Read the result of an analysis as a csv file into a dictionary.

    Args:
        csv_file_path: The path to the csv file to read the results from.
        candidate_attributes: The candidate attributes for which to read the
                              results.

    Returns:
        A dictionary associating each attribute to the analysis result.
    """
    result_dict = {}
    logger.info(f'Reading the file {csv_file_path}...')
    with open(csv_file_path, 'r') as csv_file:
        csv_file_reader = csv.reader(csv_file)
        next(csv_file_reader, None)  # skip the headers
        for row in csv_file_reader:
            attribute_name, attribute_value = row
            attribute = candidate_attributes.get_attribute_by_name(
                attribute_name)
            result_dict[attribute] = float(attribute_value)
            logger.debug(f'  {attribute_name} = {attribute_value}')
    return result_dict
