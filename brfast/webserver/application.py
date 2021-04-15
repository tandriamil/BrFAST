#!/usr/bin/python3
"""Run the Flask webserver. Note that it is multithreaded by default."""

import secrets

from flask import (flash, Flask, json, redirect, request, render_template,
                   url_for)
from loguru import logger
from werkzeug.utils import secure_filename

from brfast.data import (Attribute, AttributeSet,
                         FingerprintDatasetFromCSVInMemory)
from brfast.exploration import State, TraceData
from brfast.measures.sample.attribute_subset import AttributeSubsetSample
from brfast.webserver.file_utils import allowed_extension

# Global variables used for the backend application
FLASH_CAT_TO_CLASS = {'error': 'danger', 'warning': 'warning', 'info': 'info',
                      'success': 'success'}
UPLOAD_FOLDER = '/tmp'

# The flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = secrets.token_bytes(32)

# Parameters for the webserver
BOOTSTRAP_PROGRESS_BARS = ['', '-success', '-info', '-warning', '-danger']
FINGERPRINT_SAMPLE_SIZE = 10

# Global variables used to share data between the pages
FINGERPRINT_DATASET = None
TRACE_DATA = None


@app.route('/')
def index():
    """Show the index page."""
    return render_template('index.html')


# ================================ Trace Replay ===============================
@app.route('/trace-configuration', methods=['GET', 'POST'])
def trace_configuration():
    """Configure the assets for a trace replay."""
    global FINGERPRINT_DATASET
    global TRACE_DATA

    # -------------------------- POST request handle --------------------------
    if request.method == 'POST':

        # ------------------- Manage the required trace file ------------------
        # Check that the trace file is in the received POST request
        if 'trace-file' not in request.files:
            flash('Missing trace file!', FLASH_CAT_TO_CLASS['error'])
            logger.error('Missing trace file from trace configuration POST.')
            return render_template('trace-configuration.html')

        # Check that the trace file is correct
        trace_file = request.files['trace-file']
        trace_filename = secure_filename(trace_file.filename)
        if not trace_file or trace_filename == '':
            flash('No selected trace file!', FLASH_CAT_TO_CLASS['error'])
            logger.error('No selected trace file in POST.')
            return render_template('trace-configuration.html')

        # Check that the extension of the trace file is allowed
        if not allowed_extension(trace_filename, expected_extension='json'):
            flash('The file extension is not allowed, json expected.',
                  FLASH_CAT_TO_CLASS['error'])
            logger.error(f'The file extension of {trace_filename} is not '
                         'allowed.')
            return render_template('trace-configuration.html')

        # The trace file is correct, set is as the trace
        if TRACE_DATA:
            logger.warning('Trace data already set but updated now.')
        TRACE_DATA = json.load(trace_file)
        logger.info('The trace is set in the session.')
        # --------- End of the management of the required trace file ----------

        # ------------ Manage the fingerprint dataset optional file -----------
        # Check that the fingerprint dataset is in the POST request
        if all(('fingerprint-dataset' in request.files,
                request.files['fingerprint-dataset'],
                request.files['fingerprint-dataset'].filename != '')):
            fp_dataset_file = request.files['fingerprint-dataset']
            fp_dataset_filename = secure_filename(fp_dataset_file.filename)

            # Check the extension of the fingerprint dataset file
            if not allowed_extension(fp_dataset_filename,
                                     expected_extension='csv'):
                flash('The fingerprint dataset file extension is not allowed, '
                      'csv expected.', FLASH_CAT_TO_CLASS['error'])
                logger.error(f'The file extension of {fp_dataset_filename} is '
                             'not allowed.')
            else:
                logger.debug('Correctly received the optional dataset file.')
                if FINGERPRINT_DATASET:
                    logger.warning('Fingerprint dataset already set but '
                                   'updated now.')
                FINGERPRINT_DATASET = FingerprintDatasetFromCSVInMemory(
                    fp_dataset_file)
                logger.debug('The fingerprint dataset is set.')
        # -- End of the management of the fingerprint dataset optional file ---

        # At the end, redirect to the trace replay page
        return redirect(url_for('trace_replay'))
        # -------------------- End of POST request handle ---------------------

    # GET request handle: just show the trace configuration page
    return render_template('trace-configuration.html')


@app.route('/trace-replay')
def trace_replay():
    """Show the trace replay page with the visualization."""
    global TRACE_DATA

    # If there is no trace data set, redirect to the trace configuration page
    if not TRACE_DATA:
        logger.warning('Trying to access trace-replay without a trace set.')
        return redirect(url_for('trace_configuration'))

    # Show the trace visualization page
    return render_template('trace-visualization.html',
                           parameters=TRACE_DATA[TraceData.PARAMETERS])


@app.route('/get-trace/<int:start>/<int:end>')
def get_trace(start, end):
    """Provide the explored attribute sets.

    Args:
        start: The id of the first explored attribute set to include.
        end: The id of the last explored attribute set to include.

    Returns:
        A json textual result with a list of the explored attribute sets or an
        empty list of there is an error or no more attribute sets.
    """
    global TRACE_DATA

    # No trace data => returns an empty list
    if not TRACE_DATA:
        logger.warning('Trying to access get-trace without a trace set.')
        return '[]'

    # Provide the explored attribute sets
    logger.info(f'Getting the trace from {start} to {end}.')
    return json.dumps(TRACE_DATA[TraceData.EXPLORATION][start:end])


# ========================= Attribute Set Information =========================
@app.route('/attribute-set/<int:attribute_set_id>')
def attribute_set_information(attribute_set_id):
    """Show information about an attribute set.

    Args:
        attribute_set_id: The id of the attribute set to show.
    """
    global TRACE_DATA
    global FINGERPRINT_DATASET
    logger.info('Getting the information about the attribute set '
                f'{attribute_set_id}.')

    # If there is no trace data, show an error and redirect to the index page
    if not TRACE_DATA:
        logger.warning('Trying to access attribute-set without a trace set.')
        flash('Accessing the attribute set information requires a trace to be '
              ' set.', FLASH_CAT_TO_CLASS['error'])
        return redirect(url_for('index'))

    # Check that there is an explored attribute set with this id in the trace
    attribute_set_infos = None
    for explored_attr_set in TRACE_DATA['exploration']:
        if explored_attr_set['id'] == attribute_set_id:
            attribute_set_infos = explored_attr_set
            break

    if not attribute_set_infos:
        logger.error(f'The attribute set id {attribute_set_id} was not found.')
        flash(f'The attribute set id {attribute_set_id} was not found.',
              FLASH_CAT_TO_CLASS['error'])
        return redirect(url_for('index'))

    # Generate the attribute set object and get the names of these attributes
    attributes = AttributeSet(
        Attribute(attribute_id, TRACE_DATA['attributes'][str(attribute_id)])
        for attribute_id in attribute_set_infos['attributes']
    )
    attribute_names = [attribute.name for attribute in attributes]

    # If there is a fingerprint dataset, compute the additional/optional
    # results from it (the subset for now)
    fingerprint_sample = None
    if FINGERPRINT_DATASET:
        attr_subset_sample = AttributeSubsetSample(
            FINGERPRINT_DATASET, attributes, FINGERPRINT_SAMPLE_SIZE)
        attr_subset_sample.execute()
        fingerprint_sample = attr_subset_sample.result
    else:
        flash('Please provide a fingerprint dataset to obtain more insight on '
              'the selected attributes', FLASH_CAT_TO_CLASS['info'])

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
    candidate_attributes_infos = TRACE_DATA['exploration'][0]

    # The total usability cost
    cost_percentage = (100 * attribute_set_infos['usability_cost']
                       / candidate_attributes_infos['usability_cost'])
    usability_cost_ratio['usability'] = (
        BOOTSTRAP_PROGRESS_BARS[0], '%.2f' % cost_percentage)

    # For each cost dimension except the "weighted" ones
    can_attrs_cost_explanation = candidate_attributes_infos['cost_explanation']
    progress_bar_class_id = 1  # 0 already taken
    for cost_dimension, cost_value in can_attrs_cost_explanation.items():
        if cost_dimension.startswith('weighted'):
            continue
        cost_percentage = (
            100 * attribute_set_infos['cost_explanation'][cost_dimension]
            / cost_value)
        usability_cost_ratio[cost_dimension] = (
            BOOTSTRAP_PROGRESS_BARS[
                progress_bar_class_id % len(BOOTSTRAP_PROGRESS_BARS)],
            '%.2f' % cost_percentage)
        progress_bar_class_id += 1

    # Display the attribute information page
    return render_template('attribute-set-information.html',
                           attribute_set_infos=attribute_set_infos,
                           attribute_names=attribute_names,
                           attribute_set_state=attribute_set_state,
                           usability_cost_ratio=usability_cost_ratio,
                           fingerprint_sample=fingerprint_sample)
