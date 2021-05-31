#!/usr/bin/python3
"""This script measures the memory (i.e., average fingerprint size)."""

import argparse
from os import path

from loguru import logger

from brfast.data.dataset import FingerprintDatasetFromCSVFile
from brfast.measures.usability_cost.memory import AverageFingerprintSize


def main():
    """Measure the average fingerprint size of a fingerprint dataset."""
    logger.info('Beginning of the measure of the average attribute size of the'
                ' fingerprint dataset...')

    # Handle the arguments
    args = handle_arguments()
    input_dataset_path = args.input_dataset[0]
    output_file_path = args.output_file[0]
    logger.info(f'Reading the fingerprint dataset from {input_dataset_path}.')
    logger.info(f'The result will be written to {output_file_path}.')

    # Create the fingerprint dataset
    fingerprint_dataset = FingerprintDatasetFromCSVFile(input_dataset_path)

    # Execute the measure
    average_fp_size_analysis = AverageFingerprintSize(fingerprint_dataset)
    average_fp_size_analysis.execute()
    average_fp_size_analysis.save_csv_result(output_file_path)


def handle_arguments() -> argparse.Namespace:
    """Collect, check and give back the arguments as a Namespace object.

    Returns:
        The arguments as a Namespace object which are accessible as properties.
    """
    # Handle the arguments
    parser = argparse.ArgumentParser(
        description='Script to measure the memory size of a dataset.')
    parser.add_argument('input_dataset', type=str, nargs=1,
                        help='The path to the input fingerprint dataset.')
    parser.add_argument('output_file', type=str, nargs=1,
                        help='The output file where to write the results to.')
    args = parser.parse_args()

    # Check the path to the dataset
    input_dataset_path = args.input_dataset[0]
    if not path.isfile(input_dataset_path):
        raise ValueError('The input_dataset should point to a valid file.')

    return args


if __name__ == '__main__':
    main()
