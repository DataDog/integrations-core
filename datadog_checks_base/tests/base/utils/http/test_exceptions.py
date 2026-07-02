# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPInvalidURLError,
    HTTPSSLError,
    HTTPStatusError,
    HTTPTimeoutError,
)


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.InvalidURL('bad-url'), HTTPInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPInvalidURLError, id='missing-schema'),
    ],
)
def test_transport_exception_mapping(raised, expected):
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', side_effect=raised):
        with pytest.raises(expected):
            http.get('http://example.test/')


def test_ssl_error_maps_to_http_ssl_error():
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', side_effect=requests.exceptions.SSLError('bad cert')):
        with mock.patch.object(RequestsWrapper, 'fetch_intermediate_certs', return_value=[]):
            with pytest.raises(HTTPSSLError):
                http.get('https://example.test/')


def test_raise_for_status_maps_to_status_error():
    response = mock.MagicMock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Client Error')
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/')
        with pytest.raises(HTTPStatusError):
            wrapped.raise_for_status()
