# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_exceptions import HTTPClientError
from datadog_checks.base.utils.requests_adapter import RequestsResponseAdapter

from . import common


class AgnosticCheck(AgentCheck):
    AGNOSTIC_HTTP = True


def _default_client(transport: common.RequestsTransport) -> RequestsWrapper:
    session = requests.Session()
    session.mount('http://', transport)
    client = RequestsWrapper({}, {}, session=session)
    client.persist_connections = True
    return client


def test_default_client_returns_requests_responses():
    # Released checks read the raw response and test isinstance against requests.Response.
    transport = common.RequestsTransport()
    transport.respond(content=b'body')

    response = _default_client(transport).get('http://example.test/')

    assert isinstance(response, requests.Response)
    assert response.raw is transport.raw_responses[0]


def test_default_client_raises_request_errors_unchanged():
    transport = common.RequestsTransport()
    error = requests.exceptions.ConnectionError('refused')
    transport.raise_exception(error)

    with pytest.raises(requests.exceptions.ConnectionError) as exc_info:
        _default_client(transport).get('http://example.test/')

    assert exc_info.value is error


def test_default_client_raises_requests_status_errors():
    transport = common.RequestsTransport()
    transport.respond(status_code=404)
    response = _default_client(transport).get('http://example.test/')

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        response.raise_for_status()

    assert not isinstance(exc_info.value, HTTPClientError)


def test_default_client_raises_auth_token_errors_unchanged():
    http = RequestsWrapper({}, {})
    http.auth_token_handler = mock.MagicMock()
    error = requests.exceptions.ConnectionError('token endpoint refused')
    http.auth_token_handler.poll.side_effect = error

    with pytest.raises(requests.exceptions.ConnectionError) as exc_info:
        http.get('http://example.test/')

    assert exc_info.value is error


@pytest.mark.parametrize(
    'check_class, agnostic',
    [pytest.param(AgentCheck, False, id='unset'), pytest.param(AgnosticCheck, True, id='opted-in')],
)
def test_check_flag_selects_the_http_contract(check_class, agnostic):
    check = check_class('test', {}, [{}])
    transport = common.RequestsTransport()
    transport.respond()
    check.http.session.mount('http://', transport)

    response = check.http.get('http://example.test/', persist=True)

    assert isinstance(response, RequestsResponseAdapter) is agnostic
