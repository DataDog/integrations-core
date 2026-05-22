# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.http_httpx import HTTPXWrapper

from .conftest import parse_basic_auth


def test_basic_auth_sent_on_request(capturing_transport, captured_requests):
    http = HTTPXWrapper(
        {'username': 'alice', 'password': 'secret'},
        {},
        transport=capturing_transport,
    )
    http.get('http://example.test/')
    assert len(captured_requests) == 1
    user, password = parse_basic_auth(captured_requests[0].headers['authorization'])
    assert user == 'alice'
    assert password == 'secret'


def test_no_auth_without_credentials(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert 'authorization' not in captured_requests[0].headers


def test_basic_auth_only_when_both_user_and_password_set(capturing_transport, captured_requests):
    http = HTTPXWrapper({'username': 'alice'}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert 'authorization' not in captured_requests[0].headers


def test_basic_auth_skipped_when_only_password_set(capturing_transport, captured_requests):
    http = HTTPXWrapper({'password': 'secret'}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert 'authorization' not in captured_requests[0].headers


def test_basic_auth_options_exposes_auth(capturing_transport):
    http = HTTPXWrapper(
        {'username': 'alice', 'password': 'secret'},
        {},
        transport=capturing_transport,
    )
    assert http.options['auth'] is not None
