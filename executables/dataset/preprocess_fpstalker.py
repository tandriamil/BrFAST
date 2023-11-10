#!/usr/bin/python3
"""Preprocessing script for the FPStalker dataset."""

import argparse
import base64
import csv
import sqlite3
from copy import copy
from os import mkdir, path
from typing import List

from loguru import logger


RAW_SQL_SCRIPT = 'tableFingerprints.sql'
FINGERPRINT_CSV_FILE = 'fingerprints.csv'
CANVAS_DIRECTORY = 'canvas'
DB_NAME = 'extensionDataScheme'
IGNORED_COLUMNS = ['counter', 'updateDate', 'endDate']
RAW_CANVAS_COLUMNS = ['canvasJS', 'webGLJs']
REPLACE_COLUMN = [('id', 'browser_id'), ('creationDate', 'time_of_collect')]
REMOVE_FROM_SQL_SCRIPT = [
    ' COLLATE utf8_unicode_ci', ' CHARACTER SET latin1',
    ' ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci']


def main():
    """Preprocess the FPStalker browser fingerprint dataset."""
    logger.info('Beginning of the preprocessing of the FPStalker dataset...')

    # Handle the arguments
    args = handle_arguments()
    sql_script_path = args.sql_script_path[0]
    output_directory = args.output_directory[0]

    if args.keep_raw_canvas:
        logger.info('We keep the base64 encoded canvases in the csv output.')
        ignored_columns = IGNORED_COLUMNS
    else:
        logger.info('We ignore the base64 encoded canvases in the csv output.')
        ignored_columns = IGNORED_COLUMNS + RAW_CANVAS_COLUMNS

    # Use an in-memory database to store this database
    logger.info('Initializing the sqlite3 in-memory database.')
    sql_connection = sqlite3.connect(':memory:')

    # Execute the SQL requests of the dataset file
    logger.info(f'Executing the SQL script from {sql_script_path}.')
    with open(sql_script_path, 'r') as sql_script_file:
        sql_script = ''
        for line in sql_script_file:
            sql_script += f'\n{clean_line(line)}'
        sql_script_cursor = sql_connection.cursor()
        sql_script_cursor.executescript(sql_script)
        sql_script_cursor.close()

    # Get the name of the columns that interest us
    column_names = get_column_names(sql_connection, ignored_columns)

    # Export to a csv file
    export_database_to_csv(sql_connection, column_names, output_directory)

    # Export the canvases as images
    export_raw_canvas_to_images(sql_connection, output_directory)


def export_database_to_csv(sql_connection: sqlite3.Connection,
                           column_names: List[str], output_directory: str):
    """Export the SQL database to a csv file.

    Args:
        sql_connection: The connection to the in-memory database.
        column_names: The name of the columns to hold.
        output_directory: The directory where to store the output files.
    """
    # Fetch all the rows of the database (add the webGLJs canvas row to get the
    # extensions)
    columns = column_names + [RAW_CANVAS_COLUMNS[1]]
    fetch_all_query = f'SELECT {", ".join(columns)} FROM {DB_NAME};'
    logger.debug(f'Executing "{fetch_all_query}".')
    fetch_all_cursor = sql_connection.cursor()
    fetch_all_result = fetch_all_cursor.execute(fetch_all_query)

    # Open the resulting csv file where to write each row
    fp_csv_path = path.join(output_directory, FINGERPRINT_CSV_FILE)
    logger.info(f'Saving the fingerprint database to {fp_csv_path}.')
    with open(fp_csv_path, 'w+') as fp_csv_file:
        fp_csv_writer = csv.writer(fp_csv_file)

        # Replace some columns and write the headers
        headers = copy(column_names)
        for header_to_replace, replacement_header in REPLACE_COLUMN:
            column_id = column_names.index(header_to_replace)
            headers[column_id] = replacement_header
            logger.debug(f'Replaced the header {header_to_replace} with '
                         f'{replacement_header}.')

        fp_csv_writer.writerow(headers)
        logger.debug(f'Headers: {headers}.')

        # For each row of the database
        for row in fetch_all_result:
            # Export the list of webGL extensions
            web_gl_extensions = '§'.join(row[-1].split('§')[1:])
            row = row[:-1] + (web_gl_extensions,)
            fp_csv_writer.writerow(row)

    fetch_all_cursor.close()


def export_raw_canvas_to_images(sql_connection: sqlite3.Connection,
                                output_directory: str):
    """Export the base64 encoded canvases to image files.

    Args:
        sql_connection: The connection to the in-memory database.
        output_directory: The directory where to store the canvas images.
    """
    # Create a directory where to store the canvas images
    canvas_directory = path.join(output_directory, CANVAS_DIRECTORY)
    create_directory_if_not_exists(canvas_directory)

    # For each canvas type, create a subdirectory
    for canvas_type in RAW_CANVAS_COLUMNS:
        canvas_type_dir = path.join(canvas_directory, canvas_type)
        create_directory_if_not_exists(canvas_type_dir)

    # Fetch the raw canvases from the database
    b64_canvas_columns = []
    for canvas_type in RAW_CANVAS_COLUMNS:
        b64_canvas_columns.append(canvas_type)
        b64_canvas_columns.append(f'{canvas_type}Hashed')

    b64_canvas_query = f'SELECT {",".join(b64_canvas_columns)} FROM {DB_NAME};'
    logger.debug(f'Executing "{b64_canvas_query}".')
    b64_canvas_cursor = sql_connection.cursor()
    b64_canvas_result = b64_canvas_cursor.execute(b64_canvas_query)

    # For each row of the database then each type of raw canvas
    logger.info(f'Saving the canvas as images to {canvas_directory}.')
    for row in b64_canvas_result:
        for column_id, canvas_type in enumerate(RAW_CANVAS_COLUMNS):

            # Get the raw base64 encoded canvas and its hash representation
            raw_b64_canvas = row[column_id*2].replace(
                'data:image/png;base64,', '')
            hashed_canvas = row[column_id*2 + 1]

            # The webGLJs canvas also contains the extensions
            if canvas_type == RAW_CANVAS_COLUMNS[1]:
                raw_b64_canvas = raw_b64_canvas.split('§')[0]

            # Write the image to the file named by its hash
            canvas_image_path = path.join(canvas_directory, canvas_type,
                                          f'{hashed_canvas}.png')
            with open(canvas_image_path, 'wb+') as canvas_image_file:
                canvas_image_file.write(base64.b64decode(raw_b64_canvas))

    b64_canvas_cursor.close()


def handle_arguments() -> argparse.Namespace:
    """Collect, check and give back the arguments as a Namespace object.

    Returns:
        The arguments as a Namespace object which are accessible as properties.
    """
    # Handle the arguments
    parser = argparse.ArgumentParser(
        description='Preprocessing script for the FPStalker dataset.')
    parser.add_argument('sql_script_path', metavar='sql_script_path', type=str,
                        nargs=1, help=f'the path to {RAW_SQL_SCRIPT}.')
    parser.add_argument('output_directory', metavar='output_directory',
                        type=str, nargs=1,
                        help='the directory to store the output files.')
    parser.add_argument('--keep-raw-canvas', action='store_true',
                        help='keep the base64 encoded canvases in the output.')
    args = parser.parse_args()

    # Check the path to the dataset
    sql_script_path = args.sql_script_path[0]
    if any((not sql_script_path.endswith(RAW_SQL_SCRIPT),
            not path.isfile(sql_script_path))):
        raise ValueError('The sql_script_path should point to a valid '
                         f'{RAW_SQL_SCRIPT} file.')

    # Check the path to the output directory
    output_directory = args.output_directory[0]
    if not path.isdir(output_directory):
        raise ValueError(f'The output directory {output_directory} is not '
                         'valid.')

    return args


def get_column_names(sql_connection: sqlite3.Connection,
                     ignored_columns: List[str]) -> List[str]:
    """Retrieve the column names.

    Args:
        sql_connection: The connection to manipulate the in-memory database.
        ignored_columns: The columns to ignore.

    Returns:
        The column names to hold (i.e., these of the attributes).
    """
    # Get the name of the columns of the database
    get_columns_query = f'PRAGMA table_info({DB_NAME});'
    logger.debug(f'Executing "{get_columns_query}"...')
    get_columns_cursor = sql_connection.cursor()
    get_columns_result = get_columns_cursor.execute(get_columns_query)

    column_names = []
    for result in get_columns_result:
        _, name, _, _, _, _ = result
        if name not in ignored_columns:
            column_names.append(name)

    get_columns_cursor.close()
    return column_names


def clean_line(line: str) -> str:
    """Check whether a line of the SQL script should be executed or not.

    Args:
        line: The line to check whether sqlite3 accepts it.

    Returns:
        The line does not throw an error when read by sqlite3.
    """
    if line.startswith('SET'):
        return ''
    for part_to_remove_from_sql in REMOVE_FROM_SQL_SCRIPT:
        if part_to_remove_from_sql in line:
            line = line.replace(part_to_remove_from_sql, '')
    return line


def create_directory_if_not_exists(directory_path: str):
    """Create a directory if it does not exist.

    Args:
        directory_path: The path to the directory to create.
    """
    if not path.exists(directory_path):
        mkdir(directory_path)


if __name__ == '__main__':
    main()
