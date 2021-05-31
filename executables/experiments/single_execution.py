#!/usr/bin/python3
"""Execute the three exploration algorithms on the a given dataset.

This script requires:
- The dataset preprocessed into a 'fingerprint.csv' file.
    -> See executables.dataset.preprocess_*
- The measures of the usability cost of the attributes of the dataset
  respectively stored in 'memory.csv' and 'instability.csv'.
    -> See executables.measures.memory/instability
"""

import argparse
import importlib
from os import path
from pathlib import PurePath

from loguru import logger

from brfast.data.dataset import FingerprintDatasetFromCSVFile
from brfast.exploration.conditional_entropy import ConditionalEntropy
from brfast.exploration.entropy import Entropy
from brfast.exploration.fpselect import FPSelect
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

# The weights of the dimensions of the usability cost dimensions
USABILITY_COST_WEIGHTS = {
    CostDimension.MEMORY: 1, CostDimension.INSTABILITY: 10000}


def main():
    """Execute the three exploration methods on the dummy FPSelect example."""
    args = handle_arguments()
    data_path = PurePath(args.input_data_dir[0])
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

    # Generate the usability cost measure
    usability_cost_measure = MemoryInstability(
        memory_results, instability_results, USABILITY_COST_WEIGHTS)
    logger.info('Considering the usability cost measure '
                f'{usability_cost_measure}.')

    # Generate the sensitivity measure
    attacker_submissions = args.attacker_submissions
    sensitivity_measure = TopKFingerprints(dataset, attacker_submissions)
    logger.info(f'Considering the sensitivity measure {sensitivity_measure}.')

    # Generate the exploration method
    logger.info(f'Considering the exploration method {args.method}.')
    logger.info('Considering the sensitivity threshold '
                f'{args.sensitivity_threshold}.')

    # Entropy baseline
    if args.method == 'entropy':
        exploration = Entropy(sensitivity_measure, usability_cost_measure,
                              dataset, args.sensitivity_threshold)

    # Conditional entropy baseline
    elif args.method == 'conditional_entropy':
        exploration = ConditionalEntropy(
            sensitivity_measure, usability_cost_measure, dataset,
            args.sensitivity_threshold)

    # FPSelect
    elif args.method == 'fpselect':
        logger.info(f'Considering {args.explored_paths} explored paths.')
        if args.no_pruning:
            logger.info('Do not use the pruning methods.')
        exploration = FPSelect(
            sensitivity_measure, usability_cost_measure, dataset,
            args.sensitivity_threshold, args.explored_paths,
            not args.no_pruning)

    # Unknown method
    else:
        raise ValueError(f'Unknown exploration method {args.method}.')

    # The exploration itself
    logger.info(f'Considering the exploration method {exploration}.')
    logger.info('Beginning of the exploration...')
    exploration.run()
    solution = exploration.get_solution()
    explored_attribute_sets = len(exploration.get_explored_attribute_sets())
    logger.info(f'The solution found by {args.method} is {solution} '
                f'after exploring {explored_attribute_sets} attribute sets.')

    # Save the trace file
    if args.trace_file:
        exploration.save_exploration_trace(args.trace_file)


def handle_arguments() -> argparse.Namespace:
    """Collect, check and give back the arguments as a Namespace object.

    Returns:
        The arguments as a Namespace object which are accessible as properties.
    """
    # Handle the arguments
    parser = argparse.ArgumentParser(
        description=('Process the attribute selection on a dataset.'))
    parser.add_argument('input_data_dir', type=str, nargs=1,
                        help='The path to the directory containing the data.')
    parser.add_argument('-m', '--method', metavar='selection_method',
                        type=str, nargs='?', default='fpselect',
                        choices=['fpselect', 'entropy', 'conditional_entropy'],
                        help=('The attribute selection method (default is '
                              'fpselect)'))
    parser.add_argument('-t', '--sensitivity-threshold', metavar='threshold',
                        type=float, nargs='?', default=0.10,
                        help='The sensitivity threshold (default is 0.10).')
    parser.add_argument('-k', '--attacker-submissions', metavar='submissions',
                        type=int, nargs='?', default=4,
                        help=('The number of submissions by the attacker '
                              '(default is 4).'))
    parser.add_argument('-o', '--trace-file', metavar='trace_file',
                        type=str, nargs='?', default=None,
                        help='If set, save the trace to this file.')
    parser.add_argument('-p', '--explored-paths', metavar='paths',
                        type=int, nargs='?', default=3,
                        help=('The number of paths explored by FPSelect '
                              '(default is 3).'))
    parser.add_argument('--no-pruning', action='store_false',
                        help='Do not use the pruning methods of FPSelect.')
    args = parser.parse_args()

    # Check the path to the dataset
    input_data_dir_path = args.input_data_dir[0]
    if not path.isdir(input_data_dir_path):
        raise ValueError('The input_data_dir_path should point to a valid '
                         'directory.')

    return args


if __name__ == '__main__':
    main()
