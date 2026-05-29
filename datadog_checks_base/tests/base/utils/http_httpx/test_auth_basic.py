# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_httpx import HTTPXWrapper

from .common import parse_basic_auth


def test_basic_auth_sent_on_request(capturing_transport, captured_requests):
    http = HTTPXWrapper(
        {'username': 'alice', 'password': 'secret'},
        {},
        transport=capturing_transport,
    )
    http.get('http://example.test/')
    user, password = parse_basic_auth(captured_requests[0].headers['authorization'])
    assert user == 'alice'
    assert password == 'secret'


@pytest.mark.parametrize(
    'instance',
    [
        pytest.param({}, id='no-credentials'),
        pytest.param({'username': 'alice'}, id='username-only'),
        pytest.param({'password': 'secret'}, id='password-only'),
    ],
)
def test_no_authorization_header_set(instance, capturing_transport, captured_requests):
    http = HTTPXWrapper(instance, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert 'authorization' not in captured_requests[0].headers
