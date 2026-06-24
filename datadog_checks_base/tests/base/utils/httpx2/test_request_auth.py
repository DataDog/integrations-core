# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx2
import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper

from .common import parse_basic_auth


def test_per_request_auth_tuple_sets_basic_auth_header(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', auth=('alice', 'secret'))
    user, password = parse_basic_auth(captured_requests[0].headers['authorization'])
    assert user == 'alice'
    assert password == 'secret'


def test_per_request_auth_basicauth_instance_sets_basic_auth_header(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', auth=httpx2.BasicAuth('bob', 'hunter2'))
    user, password = parse_basic_auth(captured_requests[0].headers['authorization'])
    assert user == 'bob'
    assert password == 'hunter2'


def test_per_request_auth_shadows_client_level_auth(capturing_transport, captured_requests):
    http = HTTPX2Wrapper(
        {'username': 'alice', 'password': 'secret'},
        {},
        transport=capturing_transport,
    )
    http.get('http://example.test/', auth=('carol', 'override'))
    user, password = parse_basic_auth(captured_requests[0].headers['authorization'])
    assert user == 'carol'
    assert password == 'override'


def test_per_request_auth_alongside_other_kwargs_reaches_wire(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get(
        'http://example.test/resource',
        auth=('alice', 'secret'),
        params={'q': 'value'},
        headers={'X-Trace': 'abc'},
    )
    request = captured_requests[0]
    user, password = parse_basic_auth(request.headers['authorization'])
    assert user == 'alice'
    assert password == 'secret'
    assert request.headers['x-trace'] == 'abc'
    assert request.url.params['q'] == 'value'


@pytest.mark.parametrize(
    'auth_value',
    [
        pytest.param(('alice', 'secret'), id='tuple'),
        pytest.param(httpx2.BasicAuth('alice', 'secret'), id='basicauth'),
    ],
)
def test_per_request_auth_does_not_raise_typeerror(auth_value, capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    response = http.get('http://example.test/', auth=auth_value)
    assert response.status_code == 200
