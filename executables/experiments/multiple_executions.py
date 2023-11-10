#!/usr/bin/python3
"""Execute several attribute selections given a set of parameters.

This script requires:
- The dataset preprocessed into a 'fingerprint.csv' file.
    -> See executables.dataset.preprocess_*
- The measures of the usability cost of the attributes of the dataset
  respectively stored in 'memory.csv' and 'instability.csv'.
    -> See executables.measures.memory/instability
"""

import importlib
from os import path
from pathlib import PurePath, Path
from typing import Dict

from loguru import logger

from brfast.data.dataset import (FingerprintDataset,
                                 FingerprintDatasetFromCSVFile)
from brfast.exploration import SensitivityThresholdUnreachable
from brfast.exploration.conditional_entropy import ConditionalEntropy
from brfast.exploration.entropy import Entropy
from brfast.exploration.fpselect import FPSelect
from brfast.measures import SensitivityMeasure, UsabilityCostMeasure
from brfast.measures.sensitivity.fpselect import TopKFingerprints
from brfast.measures.usability_cost.fpselect import (
    CostDimension, MemoryInstability)

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
from executables.experiments import read_csv_analysis_as_dict
pd = importlib.import_module(params['DataAnalysis']['engine'])

# The input files for the execution
FINGERPRINT_DATASET_CSV = 'fingerprints.csv'
MEMORY_COST_CSV = 'memory.csv'
INSTABILITY_COST_CSV = 'instability.csv'

# ----------------------------- Set of Parameters -----------------------------

# Update these set of parameters to meet your needs

BASE_PATH = '[Please set this parameter first]'
DATA_DIRECTORIES = [BASE_PATH + '/FPStalker', BASE_PATH + '/HTillmann']
SELECTION_METHODS = ['entropy', 'conditional_entropy', 'fpselect']
SENSITIVITY_THRESHOLDS = [0.001, 0.005, 0.015, 0.025]
ATTACKER_SUBMISSIONS = [1, 4, 16]
USABILITY_COST_WEIGHTS = [
    # The weights used in our FPSelect paper
    {CostDimension.MEMORY: 1,  CostDimension.INSTABILITY: 10000}]
FPSELECT_EXPLORED_PATHS = [1, 3]
FPSELECT_USE_PRUNING_METHODS = True

# -------------------------- End of set of Parameters -------------------------


def main():
    """Execute the three exploration methods on the dummy FPSelect example."""
    for data_directory in DATA_DIRECTORIES:
        data_path = Path(data_directory)
        logger.debug(f'Considering the data path {data_path}.')

        # Generate the fingerprint dataset
        dataset_path = data_path.joinpath(FINGERPRINT_DATASET_CSV)
        if not path.isfile(dataset_path):
            raise ValueError(f'No fingerprint dataset is at {dataset_path}.')
        dataset = FingerprintDatasetFromCSVFile(dataset_path)
        logger.info(f'Considering the dataset {dataset}.')

        # Read the average fingerprint size and instability of the attributes
        memory_result_path = data_path.joinpath(MEMORY_COST_CSV)
        memory_results = read_csv_analysis_as_dict(
            memory_result_path, dataset.candidate_attributes)
        instability_result_path = data_path.joinpath(INSTABILITY_COST_CSV)
        instability_results = read_csv_analysis_as_dict(
            instability_result_path, dataset.candidate_attributes)

        for usability_cost_weights in USABILITY_COST_WEIGHTS:
            # Generate the usability cost measure
            usability_cost_measure = MemoryInstability(
                memory_results, instability_results, usability_cost_weights)
            logger.info('Considering the usability cost measure '
                        f'{usability_cost_measure}.')

            for attacker_submissions in ATTACKER_SUBMISSIONS:
                execute_level_1(data_path, dataset, usability_cost_measure,
                                usability_cost_weights, attacker_submissions)


def execute_level_1(data_path: PurePath, dataset: FingerprintDataset,
                    usability_cost_measure: UsabilityCostMeasure,
                    usability_cost_weights: Dict[str, float],
                    attacker_submissions: int):
    """Execute an exploration given the set of parameters."""
    # Generate the sensitivity measure
    sensitivity_measure = TopKFingerprints(dataset, attacker_submissions)
    logger.info(f'Considering the sensitivity measure {sensitivity_measure}.')

    for selection_method in SELECTION_METHODS:
        for sensitivity_threshold in SENSITIVITY_THRESHOLDS:
            execute_level_2(data_path, dataset, usability_cost_measure,
                            usability_cost_weights, attacker_submissions,
                            sensitivity_measure, selection_method,
                            sensitivity_threshold)


def execute_level_2(data_path: PurePath, dataset: FingerprintDataset,
                    usability_cost_measure: UsabilityCostMeasure,
                    usability_cost_weights: Dict[str, float],
                    attacker_submissions: int,
                    sensitivity_measure: SensitivityMeasure,
                    selection_method: str, sensitivity_threshold: float):
    """Execute an exploration given the set of parameters."""
    # Generate the exploration method
    logger.info(f'Considering the exploration method {selection_method}.')
    logger.info('Considering the sensitivity threshold '
                f'{sensitivity_threshold}.')

    # Entropy baseline
    if selection_method == 'entropy':
        exploration = Entropy(sensitivity_measure, usability_cost_measure,
                              dataset, sensitivity_threshold)

    # Conditional entropy baseline
    elif selection_method == 'conditional_entropy':
        exploration = ConditionalEntropy(
            sensitivity_measure, usability_cost_measure, dataset,
            sensitivity_threshold)

    # FPSelect
    elif selection_method == 'fpselect':
        for explored_paths in FPSELECT_EXPLORED_PATHS:
            logger.info(f'Considering {explored_paths} explored paths.')
            if FPSELECT_USE_PRUNING_METHODS:
                logger.info('Using the pruning methods.')
            exploration = FPSelect(
                sensitivity_measure, usability_cost_measure, dataset,
                sensitivity_threshold, explored_paths,
                FPSELECT_USE_PRUNING_METHODS)

            # The exploration using FPSelect
            logger.info(f'Considering the exploration method {exploration}.')
            logger.info('Beginning of the exploration...')

            try:
                exploration.run()
            except SensitivityThresholdUnreachable as stu:
                logger.warning(stu)
                return  # Quit the function

            solution = exploration.get_solution()
            explored_attribute_sets = len(
                exploration.get_explored_attribute_sets())
            logger.info(f'The solution found by {selection_method} is '
                        f' {solution} after exploring '
                        f'{explored_attribute_sets} attribute sets.')

            # Save the trace file
            trace_file_name = (str(data_path) + '/' + '-'.join([
                selection_method, str(sensitivity_threshold),
                str(attacker_submissions),
                '-'.join([
                    f'{weight}={value}'
                    for weight, value in usability_cost_weights.items()]),
                str(explored_paths)
            ]) + '.json')
            exploration.save_exploration_trace(trace_file_name)
        return

    # Unknown method
    else:
        raise ValueError(f'Unknown exploration method {selection_method}.')

    # The exploration using baselines
    logger.info(f'Considering the exploration method {exploration}.')
    logger.info('Beginning of the exploration...')

    try:
        exploration.run()
    except SensitivityThresholdUnreachable as stu:
        logger.warning(stu)
        return  # Quit the function

    solution = exploration.get_solution()
    explored_attribute_sets = len(exploration.get_explored_attribute_sets())
    logger.info(f'The solution found by {selection_method} is {solution} '
                f'after exploring {explored_attribute_sets} attribute sets.')

    # Save the trace file
    trace_file_name = (str(data_path) + '/' + '-'.join([
        selection_method, str(sensitivity_threshold),
        str(attacker_submissions),
        '-'.join([f'{weight}={value}'
                  for weight, value in usability_cost_weights.items()])
    ]) + '.json')
    exploration.save_exploration_trace(trace_file_name)


if __name__ == '__main__':
    main()
