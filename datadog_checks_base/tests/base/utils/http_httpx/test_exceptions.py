# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_connect_timeout_maps_to_timeout_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.ConnectTimeout('boom'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPTimeoutError):
        http.get('http://example.test/')


def test_read_timeout_maps_to_timeout_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.ReadTimeout('slow'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPTimeoutError):
        http.get('http://example.test/')


def test_pool_timeout_maps_to_timeout_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.PoolTimeout('pool'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPTimeoutError):
        http.get('http://example.test/')


def test_connect_error_maps_to_connection_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.ConnectError('refused'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPConnectionError):
        http.get('http://example.test/')


def test_protocol_error_maps_to_http_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.LocalProtocolError('bad'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPError):
        http.get('http://example.test/')


def test_request_error_maps_to_http_error(raising_transport_factory):
    transport = raising_transport_factory(httpx.RequestError('generic'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPError):
        http.get('http://example.test/')


def test_raise_for_status_4xx_maps_to_status_error(status_transport_factory):
    transport = status_transport_factory(404, b'not found')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_raise_for_status_5xx_maps_to_status_error(status_transport_factory):
    transport = status_transport_factory(502, b'bad gateway')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_raise_for_status_3xx_does_not_raise(status_transport_factory):
    transport = status_transport_factory(301, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    response.raise_for_status()
