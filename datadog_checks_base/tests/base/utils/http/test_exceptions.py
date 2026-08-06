# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pin the shape of the backend-agnostic HTTP exception tree.

Checks catch these by type, so the inheritance relationships are the contract. Each assertion below
records a distinction a migrated handler has to be written against, and fails if a later change
quietly merges or re-parents one of the types.
"""

import pytest
import requests

from datadog_checks.base.utils import http as http_module
from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPConnectTimeoutError,
    HTTPError,
    HTTPInvalidURLError,
    HTTPReadTimeoutError,
    HTTPRequestError,
    HTTPSSLError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.http_protocol import HTTPRequestSnapshot

pytestmark = [pytest.mark.unit]

AGNOSTIC_EXCEPTIONS = [
    HTTPError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
    HTTPConnectTimeoutError,
    HTTPReadTimeoutError,
    HTTPConnectionError,
    HTTPInvalidURLError,
    HTTPSSLError,
]


class TestHierarchy:
    @pytest.mark.parametrize('exc_type', AGNOSTIC_EXCEPTIONS, ids=lambda exc_type: exc_type.__name__)
    def test_every_type_roots_at_http_error(self, exc_type):
        assert issubclass(exc_type, HTTPError)

    def test_status_error_is_a_sibling_of_request_error(self):
        # A handler naming only HTTPRequestError does not catch a bad status, which is why the shared
        # OpenMetrics handlers name both.
        assert not issubclass(HTTPStatusError, HTTPRequestError)
        assert not issubclass(HTTPRequestError, HTTPStatusError)

    def test_both_timeout_phases_share_the_generic_timeout(self):
        assert issubclass(HTTPConnectTimeoutError, HTTPTimeoutError)
        assert issubclass(HTTPReadTimeoutError, HTTPTimeoutError)

    def test_a_timeout_is_not_a_connection_error(self):
        # requests.ConnectionError carried connect timeouts and body-phase read timeouts. Neither is
        # under HTTPConnectionError here, so a ported arm needs both types to keep its old coverage.
        assert not issubclass(HTTPTimeoutError, HTTPConnectionError)
        assert not issubclass(HTTPConnectTimeoutError, HTTPConnectionError)
        assert not issubclass(HTTPReadTimeoutError, HTTPConnectionError)

    def test_ssl_error_is_narrower_than_connection_error(self):
        # So an arm that distinguishes the two has to test HTTPSSLError first.
        assert issubclass(HTTPSSLError, HTTPConnectionError)

    def test_invalid_url_is_a_request_error(self):
        assert issubclass(HTTPInvalidURLError, HTTPRequestError)


class TestSeparationFromTheBackendTree:
    @pytest.mark.parametrize('exc_type', AGNOSTIC_EXCEPTIONS, ids=lambda exc_type: exc_type.__name__)
    def test_no_type_inherits_from_requests(self, exc_type):
        # The point of the tree: a handler written against it stays valid when the backend changes.
        assert not issubclass(exc_type, requests.exceptions.RequestException)

    @pytest.mark.parametrize('exc_type', AGNOSTIC_EXCEPTIONS, ids=lambda exc_type: exc_type.__name__)
    def test_no_type_inherits_from_os_error_or_value_error(self, exc_type):
        # Several requests types are OSError or ValueError subclasses, so arms written as
        # `except (IOError, ValueError)` do not transfer to these by inheritance.
        assert not issubclass(exc_type, (OSError, ValueError))


class TestPayload:
    def test_message_is_the_str_value(self):
        assert str(HTTPRequestError('boom')) == 'boom'

    def test_request_and_response_default_to_none(self):
        error = HTTPRequestError('boom')
        assert error.request is None
        assert error.response is None

    def test_request_snapshot_is_attached_as_given(self):
        snapshot = HTTPRequestSnapshot(method='GET', url='https://example.test/', headers={'X-Test': 'value'})
        error = HTTPStatusError('500 Server Error', request=snapshot)
        assert error.request is snapshot
        assert error.request.headers['x-test'] == 'value'


class TestReExports:
    @pytest.mark.parametrize('exc_type', AGNOSTIC_EXCEPTIONS, ids=lambda exc_type: exc_type.__name__)
    def test_available_from_the_http_module(self, exc_type):
        # Callers import the client and its exceptions from one place.
        assert getattr(http_module, exc_type.__name__) is exc_type
