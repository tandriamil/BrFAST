#!/usr/bin/python3
"""Run the Flask webserver. Note that it is multithreaded by default."""

import secrets
from csv import DictReader
from datetime import datetime
from http import HTTPStatus
from json.decoder import JSONDecodeError
from pathlib import PurePath

from flask import (abort, flash, Flask, json, jsonify, redirect, request,
                   render_template, send_file, url_for)
from loguru import logger

from brfast.config import params
from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import (FingerprintDatasetFromCSVInMemory,
                                 MissingMetadatasFields)
from brfast.exploration import ExplorationParameters, State, TraceData
from brfast.exploration.conditional_entropy import ConditionalEntropy
from brfast.exploration.entropy import Entropy
from brfast.exploration.fpselect import FPSelect
from brfast.measures.sample.attribute_subset import AttributeSetSample
from brfast.measures.distinguishability.entropy import AttributeSetEntropy
from brfast.measures.distinguishability.unicity import (
    AttributeSetUnicity, UNICITY_RATE_RESULT, UNIQUE_FPS_RESULT,
    TOTAL_BROWSERS_RESULT)
from brfast.measures.sensitivity.fpselect import TopKFingerprints
from brfast.measures.usability_cost.fpselect import (
    CostDimension, MemoryInstability, MemoryInstabilityTime)
from brfast.utils.conversion import is_str_float
from brfast.webserver.files_verification import trace_file_errors
from brfast.webserver.form_validation import (
    erroneous_field, erroneous_post_file)


# The Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = params.get('WebServer', 'upload_folder')
app.secret_key = secrets.token_bytes(
    params.getint('WebServer', 'secret_key_size'))

# Set the exploration methods, the sensitivity measures, and the usability cost
# measures below
EXPLORATION_METHODS = {'FPSelect': FPSelect, 'Entropy': Entropy,
                       'Conditional entropy': ConditionalEntropy}
SENSITIVITY_MEASURES = {'Top-k fingerprints': TopKFingerprints}
USABILITY_COST_MEASURES = {
    'Memory and instability': MemoryInstability,
    'Memory, instability, and collection time': MemoryInstabilityTime}

# The empty node that is virtually added to the explored attribute sets
EMPTY_NODE = {'time': '0:00:00.00000', 'attributes': [], 'sensitivity': 1.0,
              'usability_cost': 0, 'cost_explanation': {},
              'state': State.EMPTY_NODE, 'id': -1}

# Global variables used to share data between the pages
FINGERPRINT_DATASET = None
TRACE_DATA = None
REAL_TIME_EXPLORATION = None
EXPLORATION_PROCESS = None


@app.route('/')
def index():
    """Show the index page."""
    return render_template('index.html')


# ================================ Trace Replay ===============================
@app.route('/trace-configuration', methods=['GET', 'POST'])
def trace_configuration():
    """Configure the trace file and the optional dataset to replay a trace."""
    global TRACE_DATA
    global FINGERPRINT_DATASET
    global REAL_TIME_EXPLORATION
    global EXPLORATION_PROCESS

    # -------------------------- POST request handle --------------------------
    if request.method == 'POST':
        # ------------------- Manage the required trace file ------------------
        # Clear the previous data if there were some
        TRACE_DATA, FINGERPRINT_DATASET = None, None
        if EXPLORATION_PROCESS:
            EXPLORATION_PROCESS.terminate()
            EXPLORATION_PROCESS = None
        REAL_TIME_EXPLORATION = None

        # Check that the trace file is in the received POST request
        trace_file_error_message = erroneous_post_file(
            request, 'trace-file', expected_extension='json')
        if trace_file_error_message:
            return render_template('trace-configuration.html')

        # Load the content of the trace file as a dictionary from the json
        try:
            TRACE_DATA = json.load(request.files['trace-file'])
        except JSONDecodeError:
            error_message = 'The trace file is not correctly formated.'
            flash(error_message, params.get('WebServer', 'flash_error_class'))
            logger.error(error_message)
            return render_template('trace-configuration.html')

        # Check the content of the trace file
        if error_message := trace_file_errors(TRACE_DATA):
            flash(error_message, params.get('WebServer', 'flash_error_class'))
            logger.error(error_message)
            return render_template('trace-configuration.html')

        logger.info('The trace is correct and set.')
        # --------- End of the management of the required trace file ----------

        # ------------ Manage the optional fingerprint dataset file -----------
        # Process the fingerprint dataset file if there is one provided
        dataset_provided = ('fingerprint-dataset' in request.files
                            and request.files['fingerprint-dataset'])
        if dataset_provided:
            # Check that the fingerprint dataset is in the POST request
            fp_dataset_error_message = erroneous_post_file(
                request, 'fingerprint-dataset', expected_extension='csv')
            if not fp_dataset_error_message:
                # Try to load the fingerprint dataset, we ignore the dataset if
                # there is an error and display a warning to the user
                try:
                    FINGERPRINT_DATASET = FingerprintDatasetFromCSVInMemory(
                        request.files['fingerprint-dataset'])
                    logger.debug('The fingerprint dataset is set.')
                except MissingMetadatasFields as mmf_error:
                    error_message = ('Ignored the fingerprint dataset due to '
                                     'the error: ' + str(mmf_error))
                    flash(error_message, params.get('WebServer',
                                                    'flash_warning_class'))
                    logger.warning(error_message)
        # -- End of the management of the optional fingerprint dataset file ---

        # At the end, redirect to the trace replay page
        return redirect(url_for('trace_replay'))
        # -------------------- End of POST request handle ---------------------

    # GET request handle: just show the trace configuration page
    return render_template('trace-configuration.html')


@app.route('/trace-replay')
def trace_replay():
    """Show the trace replay page with the visualization."""
    global TRACE_DATA

    # If there is no trace data set, throw a 404 error
    if not TRACE_DATA:
        error_message = ('Accessing the trace replay page requires a '
                         'trace to be set.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Show the visualization page
    return render_template('visualization.html',
                           parameters=TRACE_DATA[TraceData.PARAMETERS],
                           javascript_parameters=params)


# =========================== Real Time Exploration ===========================
@app.route('/real-time-exploration-configuration', methods=['GET', 'POST'])
def real_time_exploration_configuration():
    """Configure the assets for a real time exploration."""
    global TRACE_DATA
    global FINGERPRINT_DATASET
    global REAL_TIME_EXPLORATION
    global EXPLORATION_PROCESS

    # The exploration methods, sensitivity and usability cost measures
    exploration_methods = list(EXPLORATION_METHODS.keys())
    sensitivity_measures = list(SENSITIVITY_MEASURES.keys())
    usability_cost_measures = list(USABILITY_COST_MEASURES.keys())

    # We store a dictionary mapping each form field to an error message if the
    # field is invalid
    errors = {}

    # -------------------------- POST request handle --------------------------
    if request.method == 'POST':
        # Clear the previous data if there were some
        TRACE_DATA, FINGERPRINT_DATASET = None, None
        if EXPLORATION_PROCESS:
            EXPLORATION_PROCESS.terminate()
            EXPLORATION_PROCESS = None
        REAL_TIME_EXPLORATION = None

        # ------------ Manage the required fingerprint dataset file -----------
        # Check that the dataset file is in the received POST request
        fp_dataset_error_message = erroneous_post_file(
            request, 'fingerprint-dataset', expected_extension='csv')
        if fp_dataset_error_message:
            errors['fingerprint-dataset'] = fp_dataset_error_message
        # --------- End of the management of the required trace file ----------

        # ------------------ Handle the sensitivity threshold -----------------
        sens_thresh_error_message = erroneous_field(
            request, 'sensitivity-threshold',
            lambda v: v and is_str_float(v) and float(v) >= 0.0,
            'The sensitivity threshold should be a positive float.')
        if sens_thresh_error_message:
            errors['sensitivity-threshold'] = sens_thresh_error_message
        else:
            sensitivity_threshold = float(
                request.form['sensitivity-threshold'])
        # -------------- End of handle the sensitivity threshold --------------

        # ------------------- Handle the exploration method -------------------
        exploration_method_error_message = erroneous_field(
            request, 'exploration-method', lambda v: v in exploration_methods,
            'The exploration method is unknown.')
        if exploration_method_error_message:
            errors['exploration-method'] = exploration_method_error_message
        else:
            exploration_method = request.form['exploration-method']
        # --------------- End of handle the exploration method ----------------

        # ------------------ Handle the FPSelect parameters -------------------
        fpselect_method_name = exploration_methods[0]
        if exploration_method == fpselect_method_name:
            use_pruning_methods = 'use-pruning-methods' in request.form

            # Check that it is a strictly positive integer comprised in the
            # expected range
            minimum_explored_paths = params.getint(
                'WebServer', 'fpselect_minimum_explored_paths')
            maximum_explored_paths = params.getint(
                'WebServer', 'fpselect_maximum_explored_paths')
            explored_paths_error_message = erroneous_field(
                request, 'explored-paths',
                lambda v: v.isdigit() and (0 < minimum_explored_paths <= int(v)
                                           <= maximum_explored_paths),
                'The number of explored paths is required to be a strictly '
                'positive integer comprised in '
                f'[{minimum_explored_paths}; {maximum_explored_paths}].')
            if explored_paths_error_message:
                errors['explored-paths'] = explored_paths_error_message
            else:
                explored_paths = int(request.form['explored-paths'])
        # -------------- End of handle the FPSelect parameters ----------------

        # ------------------ Handle the sensitivity measure -------------------
        sensitivity_measure_error_message = erroneous_field(
            request, 'sensitivity-measure',
            lambda v: v in sensitivity_measures,
            'Unknown sensitivity measure.')
        if sensitivity_measure_error_message:
            errors['sensitivity-measure'] = sensitivity_measure_error_message
        else:
            sensitivity_measure = request.form['sensitivity-measure']
        # -------------- End of handle the sensitivity measure ----------------

        # ------------- Handle the most common fingerprints (=k) --------------
        top_k_fps_sens_meas = sensitivity_measures[0]
        if sensitivity_measure == top_k_fps_sens_meas:
            minimum_common_fps = params.getint(
                'WebServer', 'top_k_fingerprints_sensitivity_measure_min_k')
            maximum_common_fps = params.getint(
                'WebServer', 'top_k_fingerprints_sensitivity_measure_max_k')

            # Check that it is a strictly positive integer and comprised in the
            # range
            top_k_fps_error_message = erroneous_field(
                request, 'most-common-fingerprints',
                lambda v: v.isdigit() and (0 < minimum_common_fps <= int(v)
                                           <= maximum_common_fps),
                'The number of explored paths is required to be a strictly '
                'positive integer and comprised in the range'
                f'[{minimum_common_fps}; {maximum_common_fps}].')
            if top_k_fps_error_message:
                errors['most-common-fingerprints'] = top_k_fps_error_message
            else:
                most_common_fingerprints = int(
                    request.form['most-common-fingerprints'])
        # --------- End of handle the most common fingerprints (=k) -----------

        # --- Initialize the dataset (needed to process the usability costs)
        candidate_attributes = None
        try:
            FINGERPRINT_DATASET = FingerprintDatasetFromCSVInMemory(
                request.files['fingerprint-dataset'])

            # We will need the candidate attributes afterwards
            candidate_attributes = FINGERPRINT_DATASET.candidate_attributes
        except MissingMetadatasFields as mmf_error:
            error_message = str(mmf_error)
            flash(error_message, params.get('WebServer', 'flash_error_class'))
            logger.error(error_message)
            errors['fingerprint-dataset'] = error_message

        logger.debug('The fingerprint dataset is set.')

        # ----------------- Handle the usability cost measure -----------------
        # The weights of the cost dimensions
        cost_dim_weights = {}

        # Check the chosen usability cost measure
        usab_cost_meas_error_message = erroneous_field(
            request, 'usability-cost-measure',
            lambda v: v in usability_cost_measures,
            'Unknown usability cost measure.')
        if usab_cost_meas_error_message:
            errors['usability-cost-measure'] = usab_cost_meas_error_message
        else:
            usability_cost_measure = request.form['usability-cost-measure']
            # All the usability cost measures for now include the memory cost
            # and the instability cost, check these two

            # The memory cost results
            memory_file_error_message = erroneous_post_file(
                request, 'memory-cost-results', expected_extension='csv')
            if memory_file_error_message:
                errors['memory-cost-results'] = memory_file_error_message

            # The memory cost weight
            memory_weight_error_message = erroneous_field(
                request, 'memory-cost-weight',
                lambda v: v and is_str_float(v) and float(v) >= 0.0,
                'The memory cost weight should be a positive float.')
            if memory_weight_error_message:
                errors['memory-cost-weight'] = memory_weight_error_message
            else:
                cost_dim_weights[CostDimension.MEMORY] = float(
                    request.form['memory-cost-weight'])

            # Read the memory cost results
            if candidate_attributes:
                memory_cost_content = (request.files['memory-cost-results']
                                       .read().decode().splitlines())
                memory_costs = {}
                mem_file_reader = DictReader(memory_cost_content)
                for row in mem_file_reader:
                    try:
                        attribute = candidate_attributes.get_attribute_by_name(
                            row['attribute'])
                        memory_costs[attribute] = float(row['average_size'])
                    except KeyError as key_error:
                        error_message = (
                            f'The {key_error.args[0]} field is missing from '
                            'the memory cost results file.')
                        flash(error_message, params.get('WebServer',
                                                        'flash_error_class'))
                        logger.error(error_message)
                        errors['memory-cost-results'] = error_message
                        break  # Exit the for loop

            # The instability cost results
            instab_file_error_message = erroneous_post_file(
                request, 'instability-cost-results', expected_extension='csv')
            if instab_file_error_message:
                errors['instability-cost-results'] = instab_file_error_message

            # The instability cost weight
            instab_weight_error_message = erroneous_field(
                request, 'instability-cost-weight',
                lambda v: v and is_str_float(v) and float(v) >= 0.0,
                'The instability cost weight should be a positive float.')
            if instab_weight_error_message:
                errors['instability-cost-weight'] = instab_weight_error_message
            else:
                cost_dim_weights[CostDimension.INSTABILITY] = float(
                    request.form['instability-cost-weight'])

            # Read the instability cost results
            if candidate_attributes:
                instability_cost_content = (
                    request.files['instability-cost-results']
                    .read().decode().splitlines())
                instability_costs = {}
                instability_file_reader = DictReader(instability_cost_content)
                for row in instability_file_reader:
                    try:
                        attribute = candidate_attributes.get_attribute_by_name(
                            row['attribute'])
                        instability_costs[attribute] = float(
                            row['proportion_of_changes'])
                    except KeyError as key_error:
                        error_message = (
                            f'The {key_error.args[0]} field is missing from '
                            'the instability cost results file.')
                        flash(error_message, params.get('WebServer',
                                                        'flash_error_class'))
                        logger.error(error_message)
                        errors['instability-cost-results'] = error_message
                        break  # Exit the for loop

            # If there is also the collection time to consider
            mem_inst_time_usab_cost = usability_cost_measures[1]
            if usability_cost_measure == mem_inst_time_usab_cost:
                # The collection time cost results
                ct_file_err_mess = erroneous_post_file(
                    request, 'collection-time-cost-results',
                    expected_extension='csv')
                if ct_file_err_mess:
                    errors['collection-time-cost-results'] = ct_file_err_mess

                # The collection time cost weight
                col_time_weight_error_message = erroneous_field(
                    request, 'collection-time-cost-weight',
                    lambda v: v and is_str_float(v) and float(v) >= 0.0,
                    'The weight of the collection time cost should be a '
                    'positive float.')
                if col_time_weight_error_message:
                    errors['collection-time-cost-weight'] = (
                        col_time_weight_error_message)
                else:
                    cost_dim_weights[CostDimension.TIME] = float(
                        request.form['collection-time-cost-weight'])

                # Read the content of the collection time results
                if candidate_attributes:
                    collection_time_content = (
                        request.files['collection-time-cost-results']
                        .read().decode().splitlines())
                    collection_time_costs = {}
                    coll_time_file_reader = DictReader(collection_time_content)
                    for row in coll_time_file_reader:
                        try:
                            attribute = (
                                candidate_attributes.get_attribute_by_name(
                                    row['attribute']))
                            collection_time_costs[attribute] = (
                                float(row['average_collection_time']),
                                bool(row['is_asynchronous']))
                        except KeyError as key_error:
                            err_mess = (
                                f'The {key_error.args[0]} field is missing '
                                'from the collection time cost results file.')
                            flash(err_mess, params.get(
                                'WebServer', 'flash_error_class'))
                            logger.error(err_mess)
                            errors['collection-time-cost-results'] = err_mess
                            break  # Exit the for loop
        # ------------- End of handle the usability cost measure --------------

        # At the end, redirect to the real time exploration page if there are
        # no errors, otherwise redirect to the configuration page.
        if not errors:
            # --- Initialize the sensitivity measure
            sens_meas_class = SENSITIVITY_MEASURES[sensitivity_measure]
            # For now on, there is only the TopKFingerprints
            actual_sens_meas = sens_meas_class(
                FINGERPRINT_DATASET, most_common_fingerprints)
            logger.debug('Initialized the sensitivity measure '
                         f'{actual_sens_meas}.')

            # --- Initialize the usability cost measure
            usab_cost_meas_class = USABILITY_COST_MEASURES[
                usability_cost_measure]

            if usability_cost_measure == mem_inst_time_usab_cost:
                # Initialize the memory, instability, and collection time
                actual_usab_cost_meas = usab_cost_meas_class(
                    memory_costs, instability_costs, collection_time_costs,
                    cost_dim_weights)
            else:
                actual_usab_cost_meas = usab_cost_meas_class(
                    memory_costs, instability_costs, cost_dim_weights)
            logger.debug('Initialized the usability cost measure '
                         f'{actual_usab_cost_meas}.')

            # --- Initialize the exploration class
            exploration_class = EXPLORATION_METHODS[exploration_method]

            # If FPSelect
            if exploration_method == fpselect_method_name:
                exploration = exploration_class(
                    actual_sens_meas, actual_usab_cost_meas,
                    FINGERPRINT_DATASET, sensitivity_threshold, explored_paths,
                    use_pruning_methods)
            else:
                exploration = exploration_class(
                    actual_sens_meas, actual_usab_cost_meas,
                    FINGERPRINT_DATASET, sensitivity_threshold)
            logger.debug(f'Initialized the exploration {exploration}.')

            # Execute the exploration in an asynchronous manner before
            REAL_TIME_EXPLORATION = exploration
            EXPLORATION_PROCESS = REAL_TIME_EXPLORATION.run_asynchronous()

            logger.debug('Redirecting to the real time exploration page')
            return redirect(url_for('real_time_exploration'))
        # -------------------- End of POST request handle ---------------------

    # Show the real time exploration configuration page
    return render_template(
        'real-time-exploration-configuration.html',
        params=params, errors=errors, exploration_methods=exploration_methods,
        sensitivity_measures=sensitivity_measures,
        usability_cost_measures=usability_cost_measures)


@app.route('/real-time-exploration')
def real_time_exploration():
    """Display the real time exploration visualization."""
    global REAL_TIME_EXPLORATION
    global EXPLORATION_PROCESS

    if not REAL_TIME_EXPLORATION or not EXPLORATION_PROCESS:
        error_message = ('Accessing the real time exploration requires a real '
                         'time exploration to be set and launched.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Show the visualization page
    return render_template('visualization.html',
                           parameters=REAL_TIME_EXPLORATION.parameters,
                           javascript_parameters=params)


# =================== Getter of the Explored Attribute Sets ===================
@app.route('/get-explored-attribute-sets/<int:start>/<int:end>')
def get_explored_attribute_sets(start: int, end: int):
    """Provide the explored attribute sets.

    Args:
        start: The id of the first explored attribute set to include.
        end: The id of the last explored attribute set to include.

    Returns:
        A json textual result with a boolean indicating if there are attribute
        sets that remain and the list of the explored attribute sets.
    """
    global TRACE_DATA
    global REAL_TIME_EXPLORATION
    global EXPLORATION_PROCESS
    data = {}

    if REAL_TIME_EXPLORATION and EXPLORATION_PROCESS:
        logger.info(f'Getting the nodes from {start} to {end} (real time).')
        data['explored_attribute_sets'] = (
            REAL_TIME_EXPLORATION.get_explored_attribute_sets(start, end))
        data['remaining'] = (data['explored_attribute_sets']
                             or EXPLORATION_PROCESS.is_alive())
        for eas_id, exp_attr_set in enumerate(data['explored_attribute_sets']):
            exp_attr_set['id'] = eas_id + start

    elif TRACE_DATA:
        logger.info(f'Getting the nodes from {start} to {end} (trace replay).')
        explored_attribute_sets = TRACE_DATA[TraceData.EXPLORATION][start:end]
        data['remaining'] = bool(explored_attribute_sets)  # False if empty
        data['explored_attribute_sets'] = explored_attribute_sets

    else:
        error_message = ('Accessing the get trace page requires a trace or a '
                         'real time exploration to be set.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Provide the explored attribute sets
    return json.dumps(data)


# ============== Getter for the trace of the current exploration ==============
@app.route('/download-trace')
def download_trace():
    """Provide the trace of the current exploration to be downloaded.

    Note:
        The file will be saved in the configured upload folder and WILL NOT be
        deleted afterwards. A trick is to use the /tmp directory for them to be
        automatically deleted.

    Returns:
        The trace of the current exploration in json format if it is finished.
    """
    global TRACE_DATA
    global REAL_TIME_EXPLORATION
    global EXPLORATION_PROCESS

    # If we are in the trace mode
    if TRACE_DATA:
        expl_params = TRACE_DATA[TraceData.PARAMETERS]

    # If there is no trace data nor real time exploration set
    elif not REAL_TIME_EXPLORATION:
        error_message = 'No real time exploration nor replayed trace is set.'
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # If there is an exploration but it has not finished yet
    elif EXPLORATION_PROCESS.is_alive():
        error_message = 'Please wait for the exploration to finish.'
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Everything is fine for the real time exploration
    else:
        expl_params = REAL_TIME_EXPLORATION.parameters

    # Get the parameters of the exploration
    method = expl_params[ExplorationParameters.METHOD].lower()
    sens_threshold = expl_params[ExplorationParameters.SENSITIVITY_THRESHOLD]

    # Everything is fine, save the exploration trace
    curr_time = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
    trace_filename = f'exploration-{curr_time}-{method}-{sens_threshold}.json'
    save_path = PurePath(app.config['UPLOAD_FOLDER']).joinpath(trace_filename)

    # Save the trace file at this path
    if TRACE_DATA:
        with open(save_path, 'w+') as saved_trace_file:
            json.dump(TRACE_DATA, saved_trace_file)
    else:
        REAL_TIME_EXPLORATION.save_exploration_trace(save_path)

    # Send the file
    return send_file(save_path, as_attachment=True)


# ========================= Attribute Set Information =========================
@app.route('/attribute-set/<int(signed=True):attribute_set_id>')
def attribute_set_information(attribute_set_id: int):
    """Show information about an attribute set.

    Args:
        attribute_set_id: The id of the attribute set to show.
    """
    global TRACE_DATA
    global FINGERPRINT_DATASET
    global REAL_TIME_EXPLORATION
    logger.info('Getting the information about the attribute set '
                f'{attribute_set_id}.')

    # Check that there is an explored attribute set with this id in the
    # trace
    attribute_set_infos = None
    if attribute_set_id == -1:
        attribute_set_infos = EMPTY_NODE
    elif REAL_TIME_EXPLORATION:
        attribute_set_infos_list = (
            REAL_TIME_EXPLORATION.get_explored_attribute_sets(
                attribute_set_id, attribute_set_id+1))
        if attribute_set_infos_list:
            attribute_set_infos = attribute_set_infos_list[0]
            attribute_set_infos['id'] = attribute_set_id
    elif TRACE_DATA:
        for explored_attr_set in TRACE_DATA['exploration']:
            if explored_attr_set['id'] == attribute_set_id:
                attribute_set_infos = explored_attr_set
                break
    else:
        error_message = ('Accessing the attribute set information page '
                         'requires a trace or a real time exploration to be '
                         'set.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    if not attribute_set_infos:
        error_message = (f'The attribute set id {attribute_set_id} was not'
                         ' found.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Generate the attribute set object and get the names of these attributes
    if REAL_TIME_EXPLORATION:
        attributes = AttributeSet(
            FINGERPRINT_DATASET.candidate_attributes.get_attribute_by_id(
                attribute_id)
            for attribute_id in attribute_set_infos['attributes'])
    elif TRACE_DATA:
        attributes = AttributeSet(
            Attribute(attribute_id,
                      TRACE_DATA['attributes'][str(attribute_id)])
            for attribute_id in attribute_set_infos['attributes'])
    attribute_names = [attribute.name for attribute in attributes]

    # If there is a fingerprint dataset, compute the additional/optional
    # results from it (the subset for now)
    fingerprint_sample = None
    if attribute_set_id == -1:
        pass  # Avoid trying to get the subset with an empty attribute set
    elif FINGERPRINT_DATASET:
        # Collect a sample of the resulting fingerprints
        attr_subset_sample = AttributeSetSample(
            FINGERPRINT_DATASET, attributes,
            params.getint('WebServer', 'fingerprint_sample_size'))
        attr_subset_sample.execute()
        fingerprint_sample = attr_subset_sample.result
    else:
        flash('Please provide a fingerprint dataset to obtain more insight on '
              'the selected attributes',
              params.get('WebServer', 'flash_info_class'))

    # Compute the textual representation of the state of this attribute set
    attribute_set_state = None
    if attribute_set_infos['state'] == State.EXPLORED:
        attribute_set_state = 'Explored'
    elif attribute_set_infos['state'] == State.PRUNED:
        attribute_set_state = 'Pruned'
    elif attribute_set_infos['state'] == State.SATISFYING:
        attribute_set_state = 'Satisfying the threshold'
    elif attribute_set_infos['state'] == State.EMPTY_NODE:
        attribute_set_state = 'Starting empty node'

    # Prepare a dictionary with the cost percentage of each dimension
    # { cost dimension => (bootstrap progress bar class,  # for pretty display
    #                      percentage of the cost of the candidate attributes)
    # }
    usability_cost_ratio = {}
    if REAL_TIME_EXPLORATION:
        candidate_attributes_infos = (
            REAL_TIME_EXPLORATION.get_explored_attribute_sets(0, 1)[0])
    elif TRACE_DATA:
        candidate_attributes_infos = TRACE_DATA['exploration'][0]
    bootstrap_progress_bars = (params
                              .get('WebServer', 'bootstrap_progress_bars')
                              .splitlines())

    # The total usability cost
    cost_percentage = (100 * attribute_set_infos['usability_cost']
                       / candidate_attributes_infos['usability_cost'])
    usability_cost_ratio['usability'] = (bootstrap_progress_bars[0],
                                         '%.2f' % cost_percentage)

    if attribute_set_id > -1:
        # For each cost dimension except the "weighted" ones
        can_attrs_cost_explanation = candidate_attributes_infos[
            'cost_explanation']
        progress_bar_class_id = 1  # 0 already taken
        for cost_dimension, cost_value in can_attrs_cost_explanation.items():
            if cost_dimension.startswith('weighted'):
                continue
            cost_percentage = (
                100 * attribute_set_infos['cost_explanation'][cost_dimension]
                / cost_value)
            usability_cost_ratio[cost_dimension] = (
                bootstrap_progress_bars[
                    progress_bar_class_id % len(bootstrap_progress_bars)],
                '%.2f' % cost_percentage)
            progress_bar_class_id += 1

    # Display the attribute information page
    return render_template('attribute-set-information.html',
                           attribute_set_infos=attribute_set_infos,
                           attribute_names=attribute_names,
                           attribute_set_state=attribute_set_state,
                           usability_cost_ratio=usability_cost_ratio,
                           fingerprint_sample=fingerprint_sample,
                           javascript_parameters=params)


@app.route('/attribute-set-entropy/<int:attribute_set_id>')
def attribute_set_entropy(attribute_set_id: int):
    """Provide the results about the entropy of an attribute set.

    Args:
        attribute_set_id: The id of the attribute set for which to provide the
                          entropy results.
    """
    global TRACE_DATA
    global FINGERPRINT_DATASET
    global REAL_TIME_EXPLORATION
    logger.info('Getting the entropy results of the attribute set '
                f'{attribute_set_id}.')

    # Check that there is an explored attribute set with this id in the trace
    attribute_set_infos = None
    if REAL_TIME_EXPLORATION:
        attribute_set_infos_list = (
            REAL_TIME_EXPLORATION.get_explored_attribute_sets(
                attribute_set_id, attribute_set_id+1))
        if attribute_set_infos_list:
            attribute_set_infos = attribute_set_infos_list[0]
            attribute_set_infos['id'] = attribute_set_id
    elif TRACE_DATA:
        for explored_attr_set in TRACE_DATA['exploration']:
            if explored_attr_set['id'] == attribute_set_id:
                attribute_set_infos = explored_attr_set
                break
    else:
        error_message = ('Accessing the attribute set entropy page requires a '
                         'trace or a real time exploration to be set.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    if not FINGERPRINT_DATASET:
        error_message = 'No fingerprint dataset is set.'
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    if not attribute_set_infos:
        error_message = (f'The attribute set id {attribute_set_id} was not '
                         'found.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Generate the attribute set object
    if REAL_TIME_EXPLORATION:
        attributes = AttributeSet(
            FINGERPRINT_DATASET.candidate_attributes.get_attribute_by_id(
                attribute_id)
            for attribute_id in attribute_set_infos['attributes'])
    elif TRACE_DATA:
        attributes = AttributeSet(
            Attribute(attribute_id,
                      TRACE_DATA['attributes'][str(attribute_id)])
            for attribute_id in attribute_set_infos['attributes'])

    # Compute the entropy of the resulting fingerprints
    attr_set_entropy = AttributeSetEntropy(FINGERPRINT_DATASET, attributes)
    attr_set_entropy.execute()
    entropy_result = attr_set_entropy.result

    # Return the json version of these results
    return jsonify(entropy_result)


@app.route('/attribute-set-unicity/<int:attribute_set_id>')
def attribute_set_unicity(attribute_set_id: int):
    """Provide the results about the unicity of an attribute set.

    Args:
        attribute_set_id: The id of the attribute set for which to provide the
                          unicity results.
    """
    global TRACE_DATA
    global FINGERPRINT_DATASET
    global REAL_TIME_EXPLORATION
    logger.info('Getting the unicity results of the attribute set '
                f'{attribute_set_id}.')

    # Check that there is an explored attribute set with this id in the trace
    attribute_set_infos = None
    if REAL_TIME_EXPLORATION:
        attribute_set_infos_list = (
            REAL_TIME_EXPLORATION.get_explored_attribute_sets(
                attribute_set_id, attribute_set_id+1))
        if attribute_set_infos_list:
            attribute_set_infos = attribute_set_infos_list[0]
            attribute_set_infos['id'] = attribute_set_id
    elif TRACE_DATA:
        for explored_attr_set in TRACE_DATA['exploration']:
            if explored_attr_set['id'] == attribute_set_id:
                attribute_set_infos = explored_attr_set
                break
    else:
        error_message = ('Accessing the attribute set unicity page requires a '
                         'trace or a real time exploration to be set.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    if not FINGERPRINT_DATASET:
        error_message = 'No fingerprint dataset is set.'
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    if not attribute_set_infos:
        error_message = (f'The attribute set id {attribute_set_id} was not '
                         'found.')
        logger.error(error_message)
        abort(HTTPStatus.NOT_FOUND, description=error_message)

    # Generate the attribute set object
    if REAL_TIME_EXPLORATION:
        attributes = AttributeSet(
            FINGERPRINT_DATASET.candidate_attributes.get_attribute_by_id(
                attribute_id)
            for attribute_id in attribute_set_infos['attributes'])
    elif TRACE_DATA:
        attributes = AttributeSet(
            Attribute(attribute_id,
                      TRACE_DATA['attributes'][str(attribute_id)])
            for attribute_id in attribute_set_infos['attributes'])

    # Compute the unicity of the resulting fingerprints
    attr_set_unicity = AttributeSetUnicity(FINGERPRINT_DATASET, attributes)
    attr_set_unicity.execute()
    unicity_result = attr_set_unicity.result

    # We need to format the results due to unsupported json conversions
    unicity_result[UNICITY_RATE_RESULT] = float(
        unicity_result[UNICITY_RATE_RESULT])
    unicity_result[UNIQUE_FPS_RESULT] = int(unicity_result[UNIQUE_FPS_RESULT])
    unicity_result[TOTAL_BROWSERS_RESULT] = int(
        unicity_result[TOTAL_BROWSERS_RESULT])

    # Return the json version of these results
    return jsonify(unicity_result)
