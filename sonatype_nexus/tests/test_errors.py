# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest
from unittest.mock import Mock

import requests
from requests import Response

from datadog_checks.sonatype_nexus.errors import APIError, handle_errors


class TestHandleErrors(unittest.TestCase):
    def setUp(self):
        self.method = Mock(return_value=Response())
        self.wrapper = handle_errors(self.method)

    def test_unsuccessful_status_code(self):
        self.method.return_value.status_code = 500
        with self.assertRaises(APIError):
            self.wrapper(Mock())

    def test_timeout_error(self):
        self.method.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(APIError):
            self.wrapper(Mock())

    def test_connection_error(self):
        self.method.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(APIError):
            self.wrapper(Mock())

    def test_request_error(self):
        self.method.side_effect = requests.exceptions.RequestException()
        with self.assertRaises(APIError):
            self.wrapper(Mock())

    def test_unexpected_error(self):
        self.method.side_effect = Exception()
        with self.assertRaises(APIError):
            self.wrapper(Mock())
