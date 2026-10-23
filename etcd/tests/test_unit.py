# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient, RecordedRequest
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientError, HTTPClientTimeoutError
from datadog_checks.etcd import Etcd

pytestmark = pytest.mark.unit

ENDPOINT = 'http://localhost:2379/metrics'
STATUS_ENDPOINT = 'http://localhost:2379/v3/maintenance/status'


@pytest.mark.parametrize(
    'extra_config, expected_http_options',
    [
        pytest.param({'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}, id='auth'),
        pytest.param({'ssl_verify': True}, {'verify': True}, id='legacy-tls-verify'),
        pytest.param({'ssl_verify': False}, {'verify': False}, id='legacy-tls-no-verify'),
        pytest.param({}, {'verify': True}, id='legacy-tls-default'),
        pytest.param({'prometheus_timeout': 100}, {'timeout': (100.0, 100.0)}, id='legacy-timeout'),
    ],
)
def test_config(extra_config: dict, expected_http_options: dict):
    check = Etcd('etcd', {}, [{'prometheus_url': ENDPOINT, **extra_config}])

    for option, value in expected_http_options.items():
        assert check.http.options[option] == value


@pytest.mark.parametrize('leader, expected', [('1', True), ('2', False)])
def test_leader_status(fake_http: FakeHTTPClient, fake_http_response: Callable, leader: str, expected: bool):
    fake_http_response(STATUS_ENDPOINT, method='POST', json_data={'leader': leader, 'header': {'member_id': '1'}})
    check = Etcd('etcd', {}, [{'prometheus_url': ENDPOINT}])

    assert check.is_leader(check.instance) is expected
    fake_http.assert_requests([RecordedRequest('POST', STATUS_ENDPOINT, {'data': '{}'})])
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize('error_type', [HTTPClientConnectionError, HTTPClientTimeoutError])
def test_unavailable_leader_status(fake_http: FakeHTTPClient, error_type: type[HTTPClientError]):
    fake_http.register_response('POST', STATUS_ENDPOINT, error_type('Gateway unavailable'))
    check = Etcd('etcd', {}, [{'prometheus_url': ENDPOINT}])
    tags = []

    check.add_leader_state_tag(check.instance, tags)

    assert tags == []
    fake_http.assert_requests([RecordedRequest('POST', STATUS_ENDPOINT, {'data': '{}'})])
    fake_http.assert_all_responses_consumed()
