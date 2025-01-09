# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest
from unittest.mock import Mock
from requests import Response
from datadog_checks.sonatype_nexus.errors import (
    APIError,
    EmptyResponseError,
    handle_errors,
    InsufficientAPIPermissionError,
    InvalidAPICredentialsError,
)


class TestHandleErrors(unittest.TestCase):
    def test_empty_response(self):
        method = Mock(return_value=None)
        wrapped_method = handle_errors(method)
        with self.assertRaises(EmptyResponseError):
            wrapped_method(Mock())

    def test_invalid_api_credentials(self):
        method = Mock(return_value=Response())
        method.return_value.status_code = 401
        wrapped_method = handle_errors(method)
        with self.assertRaises(InvalidAPICredentialsError):
            wrapped_method(Mock())

    def test_insufficient_api_permission(self):
        method = Mock(return_value=Response())
        method.return_value.status_code = 403
        wrapped_method = handle_errors(method)
        with self.assertRaises(InsufficientAPIPermissionError):
            wrapped_method(Mock())

    def test_unsuccessful_status_code(self):
        method = Mock(return_value=Response())
        method.return_value.status_code = 500
        wrapped_method = handle_errors(method)
        with self.assertRaises(APIError):
            wrapped_method(Mock())
