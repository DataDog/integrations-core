# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Client-level tests: authentication, envelope unwrapping, and pagination.

These exercise the layer between HTTP and the collectors. The envelope tests matter most:
Catalyst Center returns errors in the same `response` slot it uses for real data, so a
client that only checks the HTTP status hands an error object to a collector, which iterates
it without raising and records nothing. That failure is silent and survives code review.
"""

from __future__ import annotations

import pytest
import requests

from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.errors import CatalystApiError

from .common import ScriptedHttp, load_captured


def test_get_list_given_data_api_envelope_returns_response_items(client, respond):
    respond(load_captured('data_network_devices'))

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert devices[0]['name'] == 'sw1'


#: Every shape Catalyst Center uses to report a failure, and what the client must surface for it.
#: The appliance puts errors in the same `response` slot it uses for real records, so a client
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
        # Measured at 20, well below the default, so the lookup is doing something.
        ('/dna/data/api/v1/siteHealthSummaries', 20),
        # No entry in the table: an endpoint nobody has probed must still be paginated.
        ('/dna/intent/api/v1/some-unprobed-endpoint', 500),
    ],
)
def test_get_list_uses_the_measured_page_limit_for_the_endpoint(client, respond_sequence, path, limit):
    # Each ceiling was measured against the appliance and they are all different. Exceeding one
    # fails the whole call with errorCode 2005 rather than clamping, so an endpoint that fell
    # back to the default when it has a lower ceiling would silently collect nothing. The table
    # itself lives in constants.py next to the measurements; restating every row here would not
    # make any of them more true, so this pins the lookup and the fallback instead.
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


@pytest.mark.parametrize(
    'failure',
    [
        pytest.param(requests.exceptions.ReadTimeout('Read timed out. (read timeout=10)'), id='read-timeout'),
        pytest.param(requests.exceptions.ConnectionError('Connection reset by peer'), id='connection-reset'),
        pytest.param(
            {'status_code': 200, 'json': requests.exceptions.JSONDecodeError('Expecting value', '<html>', 0)},
            id='body-that-is-not-json',
        ),
    ],
)
def test_get_list_given_a_transport_failure_raises_catalyst_api_error(client, respond_sequence, failure):
    # Collectors skip a failed device family group, device or site only when the failure is a
    # `CatalystApiError`. A raw `requests` exception would bypass that and fail the whole collector;
    # for assurance events that leaves the window unadvanced, so the next cycle re-submits every
    # group that had already succeeded.
    respond_sequence([failure])

    with pytest.raises(CatalystApiError, match='networkDevices'):
        client.get_list('/dna/data/api/v1/networkDevices')


def test_get_list_given_429_waits_for_the_retry_after_header_then_succeeds(client, respond_sequence, sleeps):
    # The documented limit varies 20-500 requests per minute per endpoint, so 429 is expected
    # traffic rather than an exceptional condition.
    throttled = {'status_code': 429, 'json': {}, 'headers': {'Retry-After': '7'}}
    respond_sequence([throttled, load_captured('data_network_devices')])

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert sleeps == [7.0], 'Retry-After must be honoured rather than replaced by a backoff guess'


def test_get_list_given_persistent_429_backs_off_then_gives_up(client, respond_sequence, sleeps):
    # With no Retry-After to honour, the client picks its own waits. Recovery is covered above;
    # what this pins is the shape of the give-up path, because an appliance that is already
    # rate-limiting must not be retried forever at a fixed interval.
    throttled = {'status_code': 429, 'json': {}}
    requests = respond_sequence([throttled, throttled, throttled])

    with pytest.raises(CatalystApiError, match='rate limit'):
        client.get_list('/dna/data/api/v1/networkDevices')

    assert len(requests) == 3, 'bounded attempts; a throttled appliance must not be retried forever'
    assert len(sleeps) == 2, 'no point waiting after the final attempt, only between them'
    assert sleeps[1] > sleeps[0], 'each successive wait should be longer'


@pytest.mark.parametrize(
    'retry_after, expected_wait',
    [
        pytest.param('600', 30.0, id='longer-than-the-cap'),
        pytest.param('-5', 0.0, id='negative'),
    ],
)
def test_get_list_given_an_out_of_range_retry_after_clamps_the_wait(
    client, respond_sequence, sleeps, retry_after, expected_wait
):
    # Retry-After is the one wait the check does not choose. Honouring 600 would hold an Agent
    # check runner for ten minutes per throttled request, and a negative value makes `time.sleep`
    # raise.
    throttled = {'status_code': 429, 'json': {}, 'headers': {'Retry-After': retry_after}}
    respond_sequence([throttled, load_captured('data_network_devices')])

    client.get_list('/dna/data/api/v1/networkDevices')

    assert sleeps == [expected_wait]


def test_authenticate_given_429_waits_then_succeeds(instance, sleeps):
    # `_authenticate()` cannot share `_send_with_throttle_retry()`: that helper calls
    # `_ensure_token()` before every attempt, and `_ensure_token()` calls `_authenticate()`
    # whenever there is no token yet, so routing this retry through it would recurse on the very
    # first authentication. Its own loop needs pinning separately from the GET/POST tests above.
    http = ScriptedHttp(
        [load_captured('data_network_devices')],
        auth_script=[{'status_code': 429, 'json': {}, 'headers': {'Retry-After': '3'}}],
    )
    client = CatalystCenterClient(instance, http=http)

    devices = client.get_list('/dna/data/api/v1/networkDevices')

    assert len(devices) == 4
    assert client.auth_count == 1, 'the throttled attempt must not count as a successful authentication'
    assert sleeps == [3.0], 'Retry-After must be honoured for authentication the same as for GET/POST'


def test_post_object_sends_the_body_and_the_auth_token(client, respond_sequence):
    # The analytics endpoints are POST and answer with an object, not a list.
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


def test_post_object_given_expired_token_reauthenticates_and_retries_once(client, respond_sequence):
    # `_post_body` and `_get_body` share `_retry_once_on_unauthorized`, so this pins that POST is
    # wired into it at all: an analytics query's token can age out mid-cycle exactly like a GET's.
    unauthorized = {'status_code': 401, 'json': {'exp': 'token expired at X , now Y'}}
    requests = respond_sequence([unauthorized, load_captured('data_clients_summary_analytics')])

    payload = client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body={'groupBy': ['ssid']})

    assert 'aggregateAttributes' in payload
    assert client.auth_count == 2, 'expected one initial auth plus one refresh after the 401'
    assert len(requests) == 2
    assert requests[1]['extra_headers']['X-Auth-Token'] == 'token-2', 'retry must not reuse the stale token'


def test_post_object_given_repeated_401_raises_instead_of_looping(client, respond_sequence):
    unauthorized = {'status_code': 401, 'json': {'exp': 'token expired'}}
    respond_sequence([unauthorized, unauthorized])

    with pytest.raises(CatalystApiError, match='authentication'):
        client.post_object('/dna/data/api/v1/clients/summaryAnalytics', body={})

    assert client.auth_count == 2, 'must not re-authenticate indefinitely'


def test_client_given_host_with_scheme_does_not_double_prefix(instance):
    instance['catalyst_center_host'] = 'https://catalyst.example.com'

    client = CatalystCenterClient(instance, http=None)

    assert client.base_url == 'https://catalyst.example.com'


def test_client_given_host_with_http_scheme_upgrades_to_https(instance):
    # `spec.yaml` documents HTTPS as always-on; a host that ignores its "do not include a
    # scheme" instruction and supplies `http://` must not get an unencrypted connection instead.
    instance['catalyst_center_host'] = 'http://catalyst.example.com'

    client = CatalystCenterClient(instance, http=None)

    assert client.base_url == 'https://catalyst.example.com'
