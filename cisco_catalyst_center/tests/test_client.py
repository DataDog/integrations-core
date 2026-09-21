# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Client-level tests: authentication, envelope unwrapping, and pagination.

These exercise the layer between HTTP and the collectors. The envelope tests matter most:
Catalyst Center returns errors in the same ``response`` slot it uses for real data, so a
client that only checks the HTTP status hands an error object to a collector, which iterates
it without raising and records nothing. That failure is silent and survives code review.
"""

from __future__ import annotations

import pytest

from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.errors import CatalystApiError

from .common import load_captured


def test_get_list_given_data_api_envelope_returns_response_items(client, respond):
    respond(load_captured('data_network_devices'))

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert devices[0]['name'] == 'sw1'


#: Every shape Catalyst Center uses to report a failure, and what the client must surface for it.
#: The appliance puts errors in the same ``response`` slot it uses for real records, so a client
#: that reads only the HTTP status hands an error object to a collector, which iterates it without
#: raising and records nothing.
ERROR_ENVELOPES = [
    # A 400-class error as a single-element list, in the slot real records use. Numeric errorCode.
    ('error_invalid_attribute', 200, 'get_list', 'Invalid attribute provided', 14001),
    # The slot `intent_stack` uses for a real object. errorCode here is a string, not an int.
    ('error_bad_uuid_registered_route', 200, 'get_object', 'deviceId is not in UUID format', 'Bad request'),
    # An unregistered route: a bare {"error": ...} with no `response` key at all, and no code.
    ('error_route_not_found', 200, 'get_list', 'BAPI not found', None),
    # HTTP 200 with an errorMessage and an empty response. raise_for_status() would pass this.
    ('intent_application_health_missing_param', 200, 'get_list', 'must be provided', None),
    # A real 400 carrying two errorCode 2046 entries, only the first of which explains anything.
    # The body's sentence must win over the bare status.
    ('error_invalid_time_window', 400, 'get_list', 'valid EndTime timestamp', 2046),
]


@pytest.mark.parametrize(('fixture', 'status_code', 'call', 'expected_message', 'expected_code'), ERROR_ENVELOPES)
def test_request_given_an_error_envelope_raises_with_the_cisco_message(
    client, respond_sequence, fixture, status_code, call, expected_message, expected_code
):
    respond_sequence([{'status_code': status_code, 'json': load_captured(fixture)}])

    with pytest.raises(CatalystApiError) as excinfo:
        getattr(client, call)('/dna/data/api/v1/networkDevices')

    assert expected_message in str(excinfo.value)
    assert excinfo.value.error_code == expected_code


def test_get_object_given_real_object_returns_it(client, respond):
    respond(load_captured('intent_stack'))

    stack = client.get_object('/dna/intent/api/v1/network-device/abc/stack')

    assert 'deviceId' in stack


def test_get_scalar_given_count_envelope_returns_int(client, respond):
    respond(load_captured('intent_network_device_count'))

    assert client.get_scalar('/dna/intent/api/v1/network-device/count') == 4


def test_get_bare_array_given_unwrapped_list_returns_items(client, respond):
    # Some intent endpoints return a naked JSON array with no envelope whatsoever.
    respond(load_captured('intent_event_series'))

    assert len(client.get_bare_array('/dna/intent/api/v1/event-series')) == 20


def test_get_list_given_full_first_page_requests_offset_one_then_next(client, respond_sequence):
    # Offset is 1-based; Catalyst Center rejects offset=0 with errorCode 2511.
    full = {'response': [{'id': n} for n in range(500)], 'version': '1.0'}
    tail = {'response': [{'id': 500}], 'version': '1.0'}
    requests = respond_sequence([full, tail])

    records = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(records) == 501
    assert [call['params']['offset'] for call in requests] == [1, 501]


def test_get_list_given_short_first_page_makes_one_request(client, respond_sequence):
    requests = respond_sequence([load_captured('data_network_devices')])

    client.get_list('/dna/data/api/v1/networkDevices')

    assert len(requests) == 1


@pytest.mark.parametrize(
    ('path', 'limit'),
    [
        ('/dna/data/api/v1/networkDevices', 500),
        ('/dna/data/api/v1/interfaces', 500),
        ('/dna/data/api/v1/siteHealthSummaries', 20),
        ('/dna/data/api/v1/assuranceEvents', 20),
        ('/dna/data/api/v1/assuranceIssues', 25),
        ('/dna/data/api/v1/virtualNetworkHealthSummaries', 100),
        ('/dna/data/api/v1/fabricSiteHealthSummaries', 100),
        ('/dna/data/api/v1/networkApplications', 100),
    ],
)
def test_get_list_uses_the_measured_page_limit_for_each_endpoint(client, respond_sequence, path, limit):
    # Every ceiling was measured against the appliance and they are all different. Exceeding one
    # fails the whole call with errorCode 2005 rather than clamping, so a wrong value here means an
    # entire domain silently collects nothing.
    requests = respond_sequence([{'response': [], 'version': '1.0'}])

    client.get_list(path)

    assert requests[0]['params']['limit'] == limit


def test_request_given_expired_token_reauthenticates_and_retries_once(client, respond_sequence):
    unauthorized = {'status_code': 401, 'json': {'exp': 'token expired at X , now Y'}}
    requests = respond_sequence([unauthorized, load_captured('data_network_devices')])

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert client.auth_count == 2, 'expected one initial auth plus one refresh after the 401'
    assert len(requests) == 2
    assert requests[1]['extra_headers']['X-Auth-Token'] == 'token-2', 'retry must not reuse the stale token'


def test_request_given_repeated_401_raises_instead_of_looping(client, respond_sequence):
    unauthorized = {'status_code': 401, 'json': {'exp': 'token expired'}}
    respond_sequence([unauthorized, unauthorized])

    with pytest.raises(CatalystApiError, match='authentication'):
        client.get_list('/dna/data/api/v1/networkDevices')

    assert client.auth_count == 2, 'must not re-authenticate indefinitely'


def test_get_list_given_http_500_without_a_body_still_raises(client, respond_sequence):
    respond_sequence([{'status_code': 500, 'json': {}}])

    with pytest.raises(CatalystApiError, match='HTTP 500'):
        client.get_list('/dna/data/api/v1/networkDevices')


def test_get_list_sends_the_minted_token_as_x_auth_token(client, respond_sequence):
    requests = respond_sequence([load_captured('data_network_devices')])

    client.get_list('/dna/data/api/v1/networkDevices')

    assert requests[0]['extra_headers']['X-Auth-Token'] == 'token-1'


def test_get_list_given_429_waits_for_the_retry_after_header_then_succeeds(client, respond_sequence, sleeps):
    # The documented limit varies 20-500 requests per minute per endpoint, so 429 is expected
    # traffic rather than an exceptional condition.
    throttled = {'status_code': 429, 'json': {}, 'headers': {'Retry-After': '7'}}
    respond_sequence([throttled, load_captured('data_network_devices')])

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert sleeps == [7.0], 'Retry-After must be honoured rather than replaced by a backoff guess'


def test_get_list_given_429_without_retry_after_backs_off(client, respond_sequence, sleeps):
    throttled = {'status_code': 429, 'json': {}}
    respond_sequence([throttled, throttled, load_captured('data_network_devices')])

    client.get_list('/dna/data/api/v1/networkDevices')

    assert len(sleeps) == 2
    assert sleeps[1] > sleeps[0], 'each successive wait should be longer'


def test_get_list_given_persistent_429_gives_up_rather_than_hammering(client, respond_sequence, sleeps):
    throttled = {'status_code': 429, 'json': {}}
    requests = respond_sequence([throttled, throttled, throttled])

    with pytest.raises(CatalystApiError, match='rate limit'):
        client.get_list('/dna/data/api/v1/networkDevices')

    assert len(requests) == 3, 'bounded attempts; a throttled appliance must not be retried forever'
    assert len(sleeps) == 2, 'no point waiting after the final attempt, only between them'


def test_post_object_returns_the_response_object(client, respond):
    # The analytics endpoints are POST and answer with an object, not a list.
    respond(load_captured('data_clients_summary_analytics'))

    payload = client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body={'groupBy': ['ssid']})

    assert 'aggregateAttributes' in payload


def test_post_object_sends_the_body_and_the_auth_token(client, respond_sequence):
    requests = respond_sequence([load_captured('data_clients_summary_analytics')])
    body = {'groupBy': ['ssid'], 'aggregateAttributes': [{'name': 'rssi', 'function': 'avg'}]}

    client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body=body)

    assert requests[0]['json'] == body
    assert requests[0]['extra_headers']['X-Auth-Token'] == 'token-1'


def test_post_object_given_an_error_envelope_raises(client, respond_sequence):
    respond_sequence([{'status_code': 400, 'json': load_captured('error_invalid_attribute')}])

    with pytest.raises(CatalystApiError, match='Invalid attribute'):
        client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body={})


def test_post_object_given_429_retries_and_succeeds(client, respond_sequence, sleeps):
    # `_post_body` and `_get_body` share `_send_with_throttle_retry`, so the back-off behaviour
    # itself is covered by the GET tests above. What this pins is that POST is wired into it at
    # all: the analytics endpoints sit under the same appliance-wide rate limit.
    throttled = {'status_code': 429, 'json': {}, 'headers': {'Retry-After': '2'}}
    respond_sequence([throttled, load_captured('data_clients_summary_analytics')])

    payload = client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body={'groupBy': ['ssid']})

    assert 'aggregateAttributes' in payload


def test_client_given_host_with_scheme_does_not_double_prefix(instance):
    instance['catalyst_center_host'] = 'https://catalyst.example.com'

    client = CatalystCenterClient(instance, http=None)

    assert client.base_url == 'https://catalyst.example.com'
