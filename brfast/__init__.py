#!/usr/bin/python3
"""Init file of the brfast base directory."""

import configparser
import os
import sys
from pathlib import PurePath


OPTION_FILE_NAME = 'config.ini'
ANALYSIS_ENGINES = ['pandas', 'modin.pandas']
MODIN_ENGINES = ['ray', 'dask']


# The configuration of BrFAST
if 'config' not in locals():
    # Read the configuration file to retrieve the configurations
    config = configparser.ConfigParser()
    current_file_absolute_path = PurePath(os.path.abspath(__file__))
    brfast_root = current_file_absolute_path.parents[1]
    config.read(os.path.join(brfast_root, OPTION_FILE_NAME))

    # Check the parameters
    if config['DataAnalysis']['engine'] not in ANALYSIS_ENGINES:
        print(f'Please configure an engine among {ANALYSIS_ENGINES}.')

    # If using the modin engine
    if config['DataAnalysis']['engine'] == 'modin.pandas':
        if config['DataAnalysis']['modin_engine'] not in MODIN_ENGINES:
            print(f'Please configure a modin engine among {MODIN_ENGINES}.')

        # Set the modin engine
        os.environ['MODIN_ENGINE'] = config['DataAnalysis']['modin_engine']
