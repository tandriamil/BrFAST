#!/usr/bin/python3
"""Init file of the brfast.config."""

import configparser
import os
import sys
import threading
from pathlib import Path, PurePath
from typing import Optional

from loguru import logger


OPTION_FILE_NAME = 'config.ini'
ANALYSIS_ENGINES = ['pandas', 'modin.pandas']
MODIN_ENGINES = ['ray', 'dask']


def check_parameter(verification: bool, error_message: Optional[str] = '',
                    success_message: Optional[str] = ''):
    """Check a parameter and exist if the parameter is incorrect.

    If the parameter is incorrect, we end the execution.

    Args:
    verification: The verification of the parameter.
    error_message: The error message to display if the parameter is
                   incorrect.
    success_message: The message to display if everything is fine.
    """
    if all((verification,
            threading.current_thread() is not threading.main_thread())):
        # Only display on the main thread to avoid having too many logs
        logger.debug(success_message)
    else:
        logger.error(error_message)
        sys.exit()


# The configuration of BrFAST is stored in the params object
if 'params' not in locals():
    # Read the configuration file to retrieve the configurations
    params = configparser.ConfigParser()
    current_file_absolute_path = PurePath(os.path.abspath(__file__))
    brfast_root = current_file_absolute_path.parents[2]
    params.read(os.path.join(brfast_root, OPTION_FILE_NAME))

    # ========================= Check the parameters ==========================

    # ===== DataAnalysis section
    # The data analysis engine
    analysis_engine = params.get('DataAnalysis', 'engine')
    check_parameter(
        analysis_engine in ANALYSIS_ENGINES,
        f'Unknown data analysis engine: received {analysis_engine} which is '
        f'not among the accepted values {ANALYSIS_ENGINES}',
        f'Setting DataAnalysis.engine = {analysis_engine}')

    # If using the modin engine, check and set the modin engine
    if analysis_engine == 'modin.pandas':
        modin_engine = params.get('DataAnalysis', 'modin_engine')
        check_parameter(
            modin_engine in MODIN_ENGINES,
            f'Unknown modin engine: received "{modin_engine}" which is not '
            f'among the accepted values {MODIN_ENGINES}',
            f'Setting DataAnalysis.modin_engine = {modin_engine}')

        # Set the modin engine
        os.environ['MODIN_ENGINE'] = modin_engine

    # ===== Multiprocessing section
    # The number of cores to let for the other processes on the system
    free_cores = params.getint('Multiprocessing', 'free_cores')
    check_parameter(
        free_cores >= 0,
        'The number of free cores should be a strictly positive integer',
        f'Setting Multiprocessing.free_cores = {free_cores}')

    # Whether we should use multiprocessing for the measures
    multiprocessing_measures = params.getboolean('Multiprocessing', 'measures')
    # Will raise a ValueError is it cannot be converted to a boolean value
    check_parameter(
        isinstance(multiprocessing_measures, bool),
        success_message='Setting Multiprocessing.measures = '
                        f'{multiprocessing_measures}')

    # Whether we should use multiprocessing for the exploration methods
    multiprocessing_explorations = params.getboolean('Multiprocessing',
                                                     'explorations')
    # Will raise a ValueError is it cannot be converted to a boolean value
    check_parameter(
        isinstance(multiprocessing_explorations, bool),
        success_message='Setting Multiprocessing.explorations = '
                        f'{multiprocessing_explorations}')

    # DO NOT use multiprocessing if modin is used. It generates errors and
    # provide no gain as modin already executes the processes in parallel
    if analysis_engine == 'modin.pandas':
        logger.warning('Modin is used, hence we desactivate homemade '
                       'multiprocessing')
        logger.warning('Updating Multiprocessing.measures to False')
        logger.warning('Updating Multiprocessing.explorations to False')
        multiprocessing_measures = multiprocessing_explorations = False

    # ===== WebServer section
    # The upload folder where to save the temporary files
    upload_foler = params.get('WebServer', 'upload_folder')
    check_parameter(
        Path(upload_foler).is_dir(),
        f'The upload folder {upload_foler} of the web server does not exist',
        f'Using the upload folder {upload_foler}')

    # The size of the secret key for some functionalities of the WebServer
    secret_key_size = params.getint('WebServer', 'secret_key_size')
    check_parameter(
        secret_key_size > 0,
        'The secret key size should be a strictly positive integer',
        'Setting WebServer.secret_key_size = '
        f'{secret_key_size}')

    # The size of the fingerprint sample on the attribute information page
    fingerprint_sample_size = params.getint(
        'WebServer', 'fingerprint_sample_size')
    check_parameter(
        fingerprint_sample_size > 0,
        'The fingerprint sample size should be a strictly positive integer',
        'Setting WebServer.fingerprint_sample_size = '
        f'{fingerprint_sample_size}')

    # The name of the classes of the bootstrap progress bars
    bootstrap_progess_bars = params.get('WebServer', 'bootstrap_progess_bars')
    bootstrap_progess_bars_as_list = bootstrap_progess_bars.splitlines()
    check_parameter(
        len(bootstrap_progess_bars_as_list) > 0,
        'The bootstrap progress bars should contain at least one class',
        'Setting WebServer.bootstrap_progess_bars = '
        f'{", ".join(bootstrap_progess_bars_as_list)}')

    # The mapping between the flash classes of Flask and the alert classes of
    # bootstrap
    for flash_class in ['error', 'warning', 'info', 'success']:
        flash_class_name = f'flash_{flash_class}_class'
        class_value = params.get('WebServer', flash_class_name)
        check_parameter(
            class_value,
            success_message=f'Setting WebServer.{flash_class_name} = '
                            f'{class_value}')

    # --- The range of the number of explored paths of FPSelect
    # Default number of explored paths
    fpselect_default_explored_paths = params.getint(
        'WebServer', 'fpselect_default_explored_paths')
    check_parameter(
        fpselect_default_explored_paths > 0,
        'The default number of explored paths by FPSelect should be a strictly'
        ' positive integer',
        'Setting WebServer.fpselect_default_explored_paths = '
        f'{fpselect_default_explored_paths}')

    # Minimum number of explored paths
    fpselect_minimum_explored_paths = params.getint(
        'WebServer', 'fpselect_minimum_explored_paths')
    check_parameter(
        0 < fpselect_minimum_explored_paths <= fpselect_default_explored_paths,
        'The minimum number of explored paths by FPSelect should be a strictly'
        ' positive integer and lower or equal to the default value',
        'Setting WebServer.fpselect_minimum_explored_paths = '
        f'{fpselect_minimum_explored_paths}')

    # Maximum number of explored paths
    fpselect_maximum_explored_paths = params.getint(
        'WebServer', 'fpselect_maximum_explored_paths')
    check_parameter(
        0 < fpselect_default_explored_paths <= fpselect_maximum_explored_paths,
        'The maximum number of explored paths by FPSelect should be a strictly'
        ' positive integer and higher or equal to both the default and the '
        'minimum value',
        'Setting WebServer.fpselect_maximum_explored_paths = '
        f'{fpselect_maximum_explored_paths}')

    # Step for the number of explored paths
    fpselect_step_explored_paths = params.getint(
        'WebServer', 'fpselect_step_explored_paths')
    fpselect_explored_paths_range = (fpselect_maximum_explored_paths
                                     - fpselect_minimum_explored_paths)
    check_parameter(
        0 < fpselect_step_explored_paths <= fpselect_explored_paths_range,
        'The step for the explored paths by FPSelect should be a strictly'
        ' positive integer and higher or equal to the range size',
        'Setting WebServer.fpselect_step_explored_paths = '
        f'{fpselect_step_explored_paths}')

    # --- The number of common fingerprints for the top-k fingerprints
    #     sensitivity measure
    # Default number of common fingerprints
    top_k_fingerprints_sensitivity_measure_default_k = params.getint(
        'WebServer', 'top_k_fingerprints_sensitivity_measure_default_k')
    check_parameter(
        top_k_fingerprints_sensitivity_measure_default_k > 0,
        'The default k for the TopKFingerprints sensitivity measure should be '
        'a strictly positive integer',
        'Setting WebServer.top_k_fingerprints_sensitivity_measure_default_k = '
        f'{top_k_fingerprints_sensitivity_measure_default_k}')

    # Minimum number of common fingerprints
    top_k_fingerprints_sensitivity_measure_min_k = params.getint(
        'WebServer', 'top_k_fingerprints_sensitivity_measure_min_k')
    check_parameter(
        0 < top_k_fingerprints_sensitivity_measure_min_k
        <= top_k_fingerprints_sensitivity_measure_default_k,
        'The minimum k for the TopKFingerprints sensitivity measure should be '
        'a strictly positive integer and lower or equal to the default value',
        'Setting WebServer.top_k_fingerprints_sensitivity_measure_min_k = '
        f'{top_k_fingerprints_sensitivity_measure_min_k}')

    # Maximum number of common fingerprints
    top_k_fingerprints_sensitivity_measure_max_k = params.getint(
        'WebServer', 'top_k_fingerprints_sensitivity_measure_max_k')
    check_parameter(
        0 < top_k_fingerprints_sensitivity_measure_default_k
        <= top_k_fingerprints_sensitivity_measure_max_k,
        'The maximum k for the TopKFingerprints sensitivity measure should be '
        'a strictly positive integer and higher or equal to the default value',
        'Setting WebServer.top_k_fingerprints_sensitivity_measure_max_k = '
        f'{top_k_fingerprints_sensitivity_measure_max_k}')

    # Step for the number of common fingerprints
    top_k_fingerprints_sensitivity_measure_step_k = params.getint(
        'WebServer', 'top_k_fingerprints_sensitivity_measure_step_k')
    top_k_fingerprints_range = (top_k_fingerprints_sensitivity_measure_max_k
                                - top_k_fingerprints_sensitivity_measure_min_k)
    check_parameter(
        0 < top_k_fingerprints_sensitivity_measure_step_k
        <= top_k_fingerprints_range,
        'The step for the k parameter of the TopKFingerprints sensitivity '
        'measure should be a strictly positive integer and higher or equal to '
        'the range for this parameter',
        'Setting WebServer.top_k_fingerprints_sensitivity_measure_step_k = '
        f'{top_k_fingerprints_sensitivity_measure_step_k}')

    # ===== VisualizationParameters section
    # The precision of the float values displayed on the web pages
    float_precision = params.getint(
        'VisualizationParameters', 'float_precision')
    check_parameter(
        float_precision > 0,
        'The float precision should be a strictly positive integer',
        f'Setting VisualizationParameters.float_precision = {float_precision}')

    # The collected nodes step (i.e., how many attribute sets are collected on
    # every tick)
    collected_nodes_step = params.getint('VisualizationParameters',
                                         'collected_nodes_step')
    check_parameter(
        collected_nodes_step > 0,
        'The collected nodes step should be a strictly positive integer',
        'Setting VisualizationParameters.collected_nodes_step = '
        f'{collected_nodes_step}')

    # The frequency on which to collect the new attribute sets
    collect_frequency = params.getint(
        'VisualizationParameters', 'collect_frequency')
    check_parameter(
        collect_frequency > 0,
        'The collect frequency should be a strictly positive integer',
        'Setting VisualizationParameters.collect_frequency = '
        f'{collect_frequency}')

    # The limit on the number of nodes that are displayed (not used for now)
    nodes_limit = params.getint('VisualizationParameters', 'nodes_limit')
    check_parameter(nodes_limit > 0,
                    'The node limits should be a strictly positive integer',
                    'Setting VisualizationParameters.nodes_limit = '
                    f'{nodes_limit}')

    # The width of the links of the visualization graph
    link_width = params.getint('VisualizationParameters', 'link_width')
    check_parameter(link_width > 0,
                    'The link width should be a strictly positive integer',
                    'Setting VisualizationParameters.link_width = '
                    f'{link_width}')

    # The opacity of the links of the visualization graph
    link_opacity = params.getfloat('VisualizationParameters', 'link_opacity')
    check_parameter(link_opacity > 0,
                    'The link opacity should be a strictly positive float',
                    'Setting VisualizationParameters.link_opacity = '
                    f'{link_opacity}')

    # The colour of the links of the visualization graph
    link_colour = params.get('VisualizationParameters', 'link_colour')
    check_parameter(
        link_colour,
        success_message='Setting VisualizationParameters.link_colour = '
                        f'{link_colour}')

    # The radius of the nodes of the visualization graph
    node_radius = params.getint('VisualizationParameters', 'node_radius')
    check_parameter(
        node_radius > 0,
        'The node radius should be a strictly positive integer',
        f'Setting VisualizationParameters.node_radius = {node_radius}')

    # The multiplicator for the radius of the nodes of the visualization graph
    # used to generate the collision radius
    node_collision_radius_multiplicator = params.getfloat(
        'VisualizationParameters', 'node_collision_radius_multiplicator')
    check_parameter(
        node_collision_radius_multiplicator > 0,
        'The node collision radius multiplicator should be a strictly '
        'positive float',
        'Setting VisualizationParameters.node_collision_radius_multiplicator ='
        f' {node_collision_radius_multiplicator}')

    # ===== NodeColour section
    # The mapping between each attribute set state and its colour
    for state in ['explored', 'pruned', 'best_solution',
                  'satisfying_sensitivity', 'empty_node', 'default']:
        state_colour = params.get('NodeColour', state)
        check_parameter(
            state_colour,
            success_message=f'Setting NodeColour.{state} = {state_colour}')
