#!/usr/bin/python3
"""Preprocessing script for the HTillmann dataset."""

import argparse
import csv
import sqlite3
from copy import copy
from hashlib import sha3_256
from os import path
from typing import List

from loguru import logger


RAW_SQL_SCRIPT = 'bfp.sql'
FINGERPRINT_CSV_FILE = 'fingerprints.csv'
DB_NAME = 'bfp'
SQL_SCRIPT_ENCODING = 'latin1'
BINARY_COLUMNS = ['plugins_hash', 'mimetypes_hash', 'fonts_hash']
IGNORED_COLUMNS = ['id', 'ip', 'port'] + BINARY_COLUMNS
REPLACE_COLUMN = [('uid', 'browser_id'), ('dt', 'time_of_collect')]
REMOVE_FROM_SQL_SCRIPT = [' unsigned', ' AUTO_INCREMENT',
                          ' ENGINE=MyISAM  DEFAULT CHARSET=utf8=23710 ']
BINARY_COLUMNS_IDS = [-2, -3, -4, -5, -6, -7]


def main():
    """Preprocess the HTillmann browser fingerprint dataset."""
    logger.info('Beginning of the preprocessing of the HTillmann dataset...')

    # Handle the arguments
    args = handle_arguments()
    sql_script_path = args.sql_script_path[0]
    output_directory = args.output_directory[0]

    # Use an in-memory database to store this database
    logger.info('Initializing the sqlite3 in-memory database.')
    sql_connection = sqlite3.connect(':memory:')

    # Execute the SQL requests of the dataset file
    logger.info(f'Executing the SQL script from {sql_script_path}.')
    with open(sql_script_path, 'r',
              encoding=SQL_SCRIPT_ENCODING) as sql_script_file:
        sql_script = ''
        for line in sql_script_file:
            sql_script += f'{clean_line(line)}\n'

        sql_script_cursor = sql_connection.cursor()
        sql_script_cursor.executescript(sql_script)
        sql_script_cursor.close()

    # Replace the binary columns by their hash string representation
    replace_binary_columns_by_their_hash(sql_connection)

    # Get the name of the columns that interest us
    column_names = get_column_names(sql_connection)

    # Export to a csv file
    export_database_to_csv(sql_connection, column_names, output_directory)


def export_database_to_csv(sql_connection: sqlite3.Connection,
                           column_names: List[str], output_directory: str):
    """Export the SQL database to a csv file.

    Args:
        sql_connection: The connection to the in-memory database.
        column_names: The name of the columns to hold.
        output_directory: The directory where to store the output files.
    """
    # Fetch all the rows of the database
    fetch_all_query = f'SELECT {",".join(column_names)} FROM {DB_NAME};'
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
            fp_csv_writer.writerow(row)

    fetch_all_cursor.close()


def replace_binary_columns_by_their_hash(sql_connection: sqlite3.Connection):
    """Replace binary columns by the sha256 hash of their binary value.

    Some columns have either '[hash]' or a Null value. If they have '[hash]',
    the column with the name suffixed by '_hash' is a binary hash which is
    badly handled in csv format.

    This function replace the long text columns by the hash representation as a
    hexadecimal string of their binary value, which is easier to handle.

    Args:
        sql_connection: The SQL connection to the in-memory database.
    """
    # Generate a new cursor to avoid its result being written down
    bin_res_cursor = sql_connection.cursor()

    # Get the value of the binary columns
    binary_query = f'SELECT id, {", ".join(BINARY_COLUMNS)} FROM {DB_NAME};'
    logger.debug(f'Executing "{binary_query}".')
    binary_results = bin_res_cursor.execute(binary_query)

    # For each row id and the binary values
    for row_id, *binary_values in binary_results:

        # For each binary column and the associated value
        for binary_column, binary_value in zip(BINARY_COLUMNS, binary_values):

            # If the value is Null (then None in python3)
            if not binary_value:
                continue

            # Retrieve the equivalent text column (fonts_hash => fonts)
            text_column = binary_column.replace('_hash', '')
            hash_str_value = hash_binary_text(binary_value)

            update_query = (f'UPDATE {DB_NAME} '
                            f'SET {text_column}="{hash_str_value}" '
                            f'WHERE id={row_id};')
            # logger.debug(f'Executing "{update_query}".')
            update_cursor = sql_connection.cursor()
            update_cursor.execute(update_query)
            update_cursor.close()


def handle_arguments() -> argparse.Namespace:
    """Collect, check and give back the arguments as a Namespace object.

    Returns:
        The arguments as a Namespace object which are accessible as properties.
    """
    # Handle the arguments
    parser = argparse.ArgumentParser(
        description='Preprocessing script for the HTillmann dataset.')
    parser.add_argument('sql_script_path', metavar='sql_script_path', type=str,
                        nargs=1, help=f'the path to {RAW_SQL_SCRIPT}.')
    parser.add_argument('output_directory', metavar='output_directory',
                        type=str, nargs=1,
                        help='the directory to store the output files.')
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


def get_column_names(sql_connection: sqlite3.Connection) -> List[str]:
    """Retrieve the column names.

    Args:
        sql_connection: The connection to manipulate the in-memory database.

    Returns:
        The column names to hold (i.e., these of the attributes).
    """
    # Generate a new cursor for this process
    cursor = sql_connection.cursor()

    # Get the name of the columns of the database
    get_columns_query = f'PRAGMA table_info({DB_NAME});'
    logger.debug(f'Executing "{get_columns_query}"...')
    get_columns_result = cursor.execute(get_columns_query)

    column_names = []
    for result in get_columns_result:
        _, name, _, _, _, _ = result
        if name not in IGNORED_COLUMNS:
            column_names.append(name)

    cursor.close()
    return column_names


def clean_line(line: str) -> bool:
    """Check whether a line of the SQL script should be executed or not.

    Args:
        line: The line to check whether sqlite3 accepts it.

    Returns:
        The line does not throw an error when read by sqlite3.
    """
    if line.startswith('SET'):
        line = ''
    if '  KEY `' in line:
        line = ''
    if 'PRIMARY KEY' in line:
        line = '   PRIMARY KEY (`id`)'
    for part_to_remove_from_sql in REMOVE_FROM_SQL_SCRIPT:
        if part_to_remove_from_sql in line:
            line = line.replace(part_to_remove_from_sql, '')
    return line


def hash_binary_text(binary_text) -> str:
    """Hash a binary text.

    Args:
        binary_text: The binary data to hash in string format.

    Returns:
        The sha3_256 hash of the binary data in hexadecimal string format.
    """
    binary_data = binary_text.encode()
    return sha3_256(binary_data).hexdigest()


if __name__ == '__main__':
    main()
