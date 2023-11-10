#!/usr/bin/python3
"""Test module of the brfast.webserver.application module."""

import mimetypes
import unittest
from http import HTTPStatus
from os import path
from pathlib import PurePath
from typing import List, Optional

from werkzeug.datastructures import FileStorage

from brfast.webserver.application import app

CONTENT_ENCODING = 'utf-8'
FILE_PATH = PurePath(path.abspath(__file__))
TESTS_BASE_DIR = FILE_PATH.parents[1]
RANDOM_FILE = (TESTS_BASE_DIR / 'assets' / 'fingerprint-datasets'
               / 'fingerprint-sample.csv')
TRACE_FILE = (TESTS_BASE_DIR / 'assets' / 'traces'
              / 'expected_trace_fpselect_multipath_pruning_on.json')

MISSING_TRACE_FILE_ERROR_MESSAGE = 'The trace file file is missing'
TRACE_FILE_WRONG_EXTENSION_ERROR_MESSAGE = (
    'The file extension of the trace file is not allowed')
TRACE_REQUIRED = 'requires a trace to be set'
TRACE_OR_EXPLORATION_REQUIRED = ('requires a trace or a real time exploration '
                                 'to be set')


class TestApplication(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self._flask_app = app
        self._client = self._flask_app.test_client()
        self._random_file = open(RANDOM_FILE, 'rb')
        self._trace_file = open(TRACE_FILE, 'rb')

    def tearDown(self):
        self._random_file.close()
        self._trace_file.close()

    def check_get_response(self, page: str, expected_status_code: HTTPStatus,
                           expected_contents: Optional[List[str]] = None):
        response = self._client.get(page, follow_redirects=True)
        self.assertEqual(response.status_code, expected_status_code)
        if expected_contents:
            for content in expected_contents:
                content_bytes = content.encode(CONTENT_ENCODING)
                self.assertIn(content_bytes, response.data)

    def check_post_response(self, page: str, post_data: dict,
                            expected_status_code: HTTPStatus,
                            expected_contents: Optional[List[str]] = None):
        response = self._client.post(page, data=post_data,
                                     follow_redirects=True)
        self.assertEqual(response.status_code, expected_status_code)
        if expected_contents:
            for content in expected_contents:
                content_bytes = content.encode(CONTENT_ENCODING)
                self.assertIn(content_bytes, response.data)

    def test_initial_state(self):
        self.check_get_response('/', HTTPStatus.OK)
        self.check_get_response('/trace-configuration', HTTPStatus.OK)

        # Pages that should not be accessible at the beginning
        self.check_get_response(
            '/trace-replay', HTTPStatus.NOT_FOUND,
            expected_contents=[TRACE_REQUIRED])
        self.check_get_response(
            '/attribute-set/1', HTTPStatus.NOT_FOUND,
            expected_contents=[TRACE_OR_EXPLORATION_REQUIRED])
        self.check_get_response(
            '/get-explored-attribute-sets/0/1', HTTPStatus.NOT_FOUND,
            expected_contents=[TRACE_OR_EXPLORATION_REQUIRED])
        self.check_get_response(
            '/attribute-set-entropy/1', HTTPStatus.NOT_FOUND,
            expected_contents=[TRACE_OR_EXPLORATION_REQUIRED])
        self.check_get_response(
            '/attribute-set-unicity/1', HTTPStatus.NOT_FOUND,
            expected_contents=[TRACE_OR_EXPLORATION_REQUIRED])

        # Pages that throw a 404 error due to the missing GET parameters
        self.check_get_response('/get-explored-attribute-sets',
                                HTTPStatus.NOT_FOUND)
        self.check_get_response('/attribute-set', HTTPStatus.NOT_FOUND)
        self.check_get_response('/attribute-set-entropy', HTTPStatus.NOT_FOUND)
        self.check_get_response('/attribute-set-unicity', HTTPStatus.NOT_FOUND)

    def test_trace_configuration_missing_trace_file(self):
        self.check_get_response('/', HTTPStatus.OK)
        self.check_get_response('/trace-configuration', HTTPStatus.OK)
        trace_configuration_data = {}
        # Redirected (HTTPStatus.OK) with an error message
        self.check_post_response(
            '/trace-configuration', post_data=trace_configuration_data,
            expected_status_code=HTTPStatus.OK,
            expected_contents=[MISSING_TRACE_FILE_ERROR_MESSAGE])

    def test_trace_configuration_trace_file_wrong_extension(self):
        self.check_get_response('/', HTTPStatus.OK)
        self.check_get_response('/trace-configuration', HTTPStatus.OK)
        trace_file = FileStorage(
            stream=self._random_file, filename=RANDOM_FILE.name,
            content_type=mimetypes.guess_type(RANDOM_FILE))
        trace_configuration_data = {'trace-file': trace_file}
        # Redirected (HTTPStatus.OK) with an error message
        self.check_post_response(
            '/trace-configuration', post_data=trace_configuration_data,
            expected_status_code=HTTPStatus.OK,
            expected_contents=[TRACE_FILE_WRONG_EXTENSION_ERROR_MESSAGE])

    # NOTE The way to handle the information as global variables renders the
    #      testing difficult as the "session" is not held using the testing
    #      client.
    #
    # def test_trace_configuration_correct_workflow(self):
    #     with self._flask_app.test_client() as test_client_context:
    #         self._client = test_client_context
    #         self.check_get_response('/', HTTPStatus.OK)
    #         self.check_get_response('/trace-configuration', HTTPStatus.OK)
    #         trace_file = FileStorage(
    #             stream=self._trace_file, filename=TRACE_FILE.name,
    #             content_type=mimetypes.guess_type(TRACE_FILE))
    #         trace_configuration_data = {'trace-file': trace_file}
    #         # Redirected (HTTPStatus.OK) to the trace replay page
    #         trace_replay_page_oracle = 'Exploration state'
    #         self.check_post_response(
    #             '/trace-configuration', post_data=trace_configuration_data,
    #             expected_status_code=HTTPStatus.BAD_REQUEST,
    #             expected_contents=[trace_replay_page_oracle])


if __name__ == '__main__':
    unittest.main()
