# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
from typing import Any

import pytest
import requests
from urllib3.exceptions import ProtocolError

from datadog_checks.dev.http import MockResponse
from datadog_checks.pan_firewall.api import (
    PanosApiError,
    PanosAuthError,
    PanosClient,
    PanosError,
    PanosSkipped,
    PanosUnreachable,
    api_url,
    transport_errors,
)
from datadog_checks.pan_firewall.auth import Credentials, KeyManager

from .common import FIXTURES, SYSTEM_INFO_CMD
from .fake_panos import TRANSPORT_ERRORS, response
from .fixture_map import op_fixture

HOST = '192.0.2.10'
URL = f'https://{HOST}/api/'
GENERATED_KEY = 'GENERATED-KEY-0123456789'
STATIC_KEY = 'STATIC-KEY-9876543210'
PASSWORD_CREDS = Credentials(username='dummy-user', password='s3cret-pw', api_key=None)
STATIC_CREDS = Credentials(username=None, password=None, api_key=STATIC_KEY)

SYSTEM_INFO = op_fixture(SYSTEM_INFO_CMD).read_bytes()
THREAT_SUBMIT = (FIXTURES / 'fw-a' / 'threat_log_5m_submit.xml').read_bytes()
THREAT_LOGS = (FIXTURES / 'fw-a' / 'threat_log_5m.xml').read_bytes()
INVALID_CREDENTIAL = (FIXTURES / 'synthetic' / 'auth_invalid_credential.xml').read_bytes()
CODE_16 = (FIXTURES / 'synthetic' / 'auth_code_16.xml').read_bytes()


def keygen_ok(key):
    """The keygen success shape (`result/key`) from the PAN-OS XML API docs. Kept inline: fixture files hold no key."""
    return f'<response status="success"><result><key>{key}</key></result></response>'.encode()


KEYGEN_OK = keygen_ok(GENERATED_KEY)
# A first key, then the one a renewal gets: a retry must carry the second.
KEY_1, KEY_2 = 'GENERATED-KEY-1', 'GENERATED-KEY-2'

# Auth rejections the client must treat as an expired key, with the HTTP status they arrive with.
AUTH_FAILURES = [
    pytest.param(403, INVALID_CREDENTIAL, id='http-403-invalid-credential'),
    pytest.param(200, INVALID_CREDENTIAL, id='code-403-in-body'),
    pytest.param(200, CODE_16, id='code-16'),
]

type Answer = tuple[int, bytes] | Exception | MockResponse


class FakeHttp:
    """Stands in for `RequestsWrapper`: records every `post` and answers keygen and API calls from two queues."""

    def __init__(self, keygen: list[Answer] | None = None, api: list[Answer] | None = None):
        self.keygen = list(keygen or [])
        self.api = list(api or [])
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **options: Any) -> MockResponse:
        self.calls.append({'url': url, **options})
        queue = self.keygen if options['data'].get('type') == 'keygen' else self.api
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, MockResponse):
            return answer
        return response(*answer)

    def calls_of(self, kind: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if (c['data'].get('type') == 'keygen') == (kind == 'keygen')]


def make_client(http: Any, creds: Credentials = PASSWORD_CREDS, log: Any = None) -> tuple[PanosClient, KeyManager]:
    keys = KeyManager(http, HOST, creds)
    return PanosClient(http, HOST, keys, log or logging.getLogger('test_api'), max_in_flight=2), keys


@pytest.mark.parametrize(
    'host, expected',
    [
        pytest.param('192.0.2.10', 'https://192.0.2.10/api/', id='ipv4'),
        pytest.param('2001:db8::1', 'https://[2001:db8::1]/api/', id='ipv6-bracketed'),
        pytest.param('panorama.example.com', 'https://panorama.example.com/api/', id='hostname'),
    ],
)
def test_api_url_is_always_on_port_443(host, expected):
    assert api_url(host) == expected


def test_keygen_posts_credentials_in_body_and_key_only_in_header():
    http = FakeHttp(keygen=[(200, KEYGEN_OK)], api=[(200, SYSTEM_INFO)])
    client, _ = make_client(http)

    root = client.op(SYSTEM_INFO_CMD)

    assert root.findtext('./result/system/hostname') == 'fw-a'
    keygen, op = http.calls
    assert keygen['url'] == URL
    assert keygen['data'] == {'type': 'keygen', 'user': 'dummy-user', 'password': 's3cret-pw'}
    assert 'extra_headers' not in keygen
    assert op['url'] == URL
    assert op['data'] == {'type': 'op', 'cmd': SYSTEM_INFO_CMD}
    assert op['extra_headers'] == {'X-PAN-KEY': GENERATED_KEY}


def test_key_never_leaks_into_urls_logs_or_errors(caplog):
    caplog.set_level(logging.DEBUG)
    http = FakeHttp(
        keygen=[(200, keygen_ok(KEY_1)), (200, keygen_ok(KEY_2))],
        api=[
            (200, SYSTEM_INFO),
            (200, THREAT_SUBMIT),
            (200, THREAT_LOGS),
            (200, THREAT_LOGS),
            (403, INVALID_CREDENTIAL),
            (403, INVALID_CREDENTIAL),
            TRANSPORT_ERRORS['refused'],
        ],
    )
    client, _ = make_client(http)
    errors = []

    client.op(SYSTEM_INFO_CMD)
    client.submit_job({'type': 'log', 'log-type': 'threat'})
    client.get_job('log', '2')
    client.read_log_job('2', lambda _entry: None)
    for _ in range(2):
        try:
            client.op(SYSTEM_INFO_CMD)
        except PanosError as e:
            errors.append(e)

    assert [type(e) for e in errors] == [PanosAuthError, PanosUnreachable]
    # The retry after the first rejection carries the renewed key.
    assert [c['extra_headers']['X-PAN-KEY'] for c in http.calls_of('api')][4:6] == [KEY_1, KEY_2]
    for call in http.calls:
        sent = ' '.join([call['url'], *call['data'].keys(), *call['data'].values()])
        assert KEY_1 not in sent and KEY_2 not in sent
        assert 'key=' not in call['url']
    for secret in (KEY_1, KEY_2, STATIC_KEY, 's3cret-pw'):
        assert secret not in caplog.text
    for error in errors:
        for key in (KEY_1, KEY_2):
            assert key not in str(error)
            assert key not in repr(error)


@pytest.mark.parametrize('status, body', AUTH_FAILURES)
def test_rejected_key_is_regenerated_once_and_the_call_retried(status, body):
    http = FakeHttp(keygen=[(200, keygen_ok(KEY_1)), (200, keygen_ok(KEY_2))], api=[(status, body), (200, SYSTEM_INFO)])
    client, _ = make_client(http)

    root = client.op(SYSTEM_INFO_CMD)

    assert root.findtext('./result/system/hostname') == 'fw-a'
    assert len(http.calls_of('keygen')) == 2
    assert [c['extra_headers']['X-PAN-KEY'] for c in http.calls_of('api')] == [KEY_1, KEY_2]
    stats = client.stats
    assert (stats.auth_rejected, stats.key_regenerated) == (False, True)


def test_key_rejected_again_after_regeneration_raises():
    http = FakeHttp(
        keygen=[(200, KEYGEN_OK), (200, KEYGEN_OK)], api=[(403, INVALID_CREDENTIAL), (403, INVALID_CREDENTIAL)]
    )
    client, _ = make_client(http)

    with pytest.raises(PanosAuthError):
        client.op(SYSTEM_INFO_CMD)

    assert len(http.calls_of('keygen')) == 2
    assert len(http.calls_of('api')) == 2


def test_log_stream_regenerates_a_rejected_key():
    http = FakeHttp(keygen=[(200, keygen_ok(KEY_1)), (200, keygen_ok(KEY_2))], api=[(200, CODE_16), (200, THREAT_LOGS)])
    client, _ = make_client(http)
    seqnos = []

    status = client.read_log_job('2', lambda entry: seqnos.append(entry.findtext('seqno')))

    assert status == 'FIN'
    assert len(seqnos) == 39
    assert http.calls_of('api')[-1]['data'] == {'type': 'log', 'action': 'get', 'job-id': '2'}
    assert http.calls_of('api')[-1]['stream'] is True
    assert [c['extra_headers']['X-PAN-KEY'] for c in http.calls_of('api')] == [KEY_1, KEY_2]
    assert len(http.calls_of('keygen')) == 2


@pytest.mark.parametrize(
    'keygen, api, keygens_before_reset',
    [
        pytest.param(
            [(403, INVALID_CREDENTIAL), (200, KEYGEN_OK)], [(200, SYSTEM_INFO)], 1, id='first-keygen-rejected'
        ),
        # The key is revoked and the credentials changed mid-run: the renewal keygen is rejected.
        pytest.param(
            [(200, KEYGEN_OK), (403, INVALID_CREDENTIAL), (200, KEYGEN_OK)],
            [(403, INVALID_CREDENTIAL), (200, SYSTEM_INFO)],
            2,
            id='renewal-keygen-rejected',
        ),
    ],
)
def test_rejected_keygen_is_not_retried_until_reset(keygen, api, keygens_before_reset):
    http = FakeHttp(keygen=keygen, api=api)
    client, keys = make_client(http)

    # The later call of the same run must not log in again.
    for _ in range(2):
        with pytest.raises(PanosAuthError):
            client.op(SYSTEM_INFO_CMD)
    assert len(http.calls_of('keygen')) == keygens_before_reset
    assert client.stats.auth_rejected is True
    # PAN-OS answered the keygen: the firewall is reachable even though the credentials are not accepted.
    assert client.stats.answered is True

    # The next run.
    client.start_run()
    client.op(SYSTEM_INFO_CMD)

    assert len(http.calls_of('keygen')) == keygens_before_reset + 1
    assert client.stats.auth_rejected is False


def test_calls_rejected_with_the_same_key_renew_it_once():
    http = FakeHttp(keygen=[(200, keygen_ok(key)) for key in (KEY_1, KEY_2, 'GENERATED-KEY-3')])
    keys = KeyManager(http, HOST, PASSWORD_CREDS)
    assert keys.key() == KEY_1

    # Two calls in flight both rejected with KEY-1: only the first regenerates, the second takes its key.
    renewed = [keys.renew(KEY_1), keys.renew(KEY_1)]

    assert renewed == [KEY_2, KEY_2]
    assert len(http.calls_of('keygen')) == 2


@pytest.mark.parametrize(
    'call',
    [
        pytest.param(lambda client: client.op(SYSTEM_INFO_CMD), id='op'),
        pytest.param(lambda client: client.read_log_job('2', lambda _entry: None), id='log-stream'),
    ],
)
@pytest.mark.parametrize(
    'answer, code',
    [
        # A proxy's 403 page says nothing about the PAN-OS key or credentials.
        pytest.param((403, b'<html><body>403 Forbidden</body></html>'), '403', id='non-panos-http-403'),
        pytest.param((200, (FIXTURES / 'fw-a-probe' / 'report_top-rules.xml').read_bytes()), '400', id='api-error'),
    ],
)
def test_error_that_is_not_an_auth_rejection_neither_renews_the_key_nor_invalidates_credentials(call, answer, code):
    http = FakeHttp(keygen=[(200, KEYGEN_OK)], api=[answer])
    client, _ = make_client(http)

    with pytest.raises(PanosApiError) as exc_info:
        call(client)

    assert type(exc_info.value) is PanosApiError
    assert exc_info.value.code == code
    assert len(http.calls_of('keygen')) == 1
    assert client.stats.auth_rejected is False


def test_static_key_is_never_regenerated():
    http = FakeHttp(api=[(403, INVALID_CREDENTIAL)])
    client, _ = make_client(http, STATIC_CREDS)

    with pytest.raises(PanosAuthError):
        client.op(SYSTEM_INFO_CMD)

    stats = client.stats
    assert (stats.auth_rejected, stats.key_regenerated) == (True, False)
    assert http.calls_of('keygen') == []
    assert http.calls[0]['extra_headers'] == {'X-PAN-KEY': STATIC_KEY}


@pytest.mark.parametrize('failure', ['timeout', 'refused', 'tls'])
def test_transport_errors_are_unreachable_and_keep_the_original_text(failure):
    raised = TRANSPORT_ERRORS[failure]
    http = FakeHttp(api=[raised])
    client, _ = make_client(http, STATIC_CREDS)

    with pytest.raises(PanosUnreachable) as exc_info:
        client.op(SYSTEM_INFO_CMD)

    assert type(exc_info.value) is PanosUnreachable
    assert str(exc_info.value) == f'could not reach {HOST}: {raised}'
    assert client.stats.unreachable == str(raised)


@pytest.mark.parametrize(
    'error_type, message',
    [
        pytest.param(requests.exceptions.ReadTimeout, 'Read timed out. (read timeout=30)', id='read-timeout'),
        pytest.param(
            requests.exceptions.ConnectTimeout, 'Connect timed out. (connect timeout=30)', id='connect-timeout'
        ),
        pytest.param(requests.exceptions.ConnectionError, 'Connection refused', id='refused'),
        pytest.param(requests.exceptions.SSLError, 'certificate verify failed', id='tls'),
    ],
)
def test_requests_exceptions_are_unreachable_without_the_key(error_type, message):
    # The `requests` exception holds the prepared request, whose headers carry the key.
    request = requests.Request('POST', URL, headers={'X-PAN-KEY': STATIC_KEY}).prepare()

    with pytest.raises(PanosUnreachable) as exc_info, transport_errors(URL):
        raise error_type(message, request=request)

    error = exc_info.value
    assert type(error) is PanosUnreachable
    assert str(error) == f'could not reach {HOST}: {message}'
    assert STATIC_KEY not in str(error) and STATIC_KEY not in repr(error)
    assert error.__cause__ is None and error.__suppress_context__


@pytest.mark.parametrize(
    'call, failure, error',
    [
        pytest.param(
            lambda client: client.op(SYSTEM_INFO_CMD),
            TRANSPORT_ERRORS['timeout'],
            PanosUnreachable,
            id='op-timeout',
        ),
        pytest.param(
            lambda client: client.read_log_job('2', lambda _entry: None),
            TRANSPORT_ERRORS['refused'],
            PanosUnreachable,
            id='log-job-refused',
        ),
    ],
)
def test_calls_after_a_timeout_or_refusal_fail_fast_until_the_next_run(call, failure, error):
    http = FakeHttp(api=[failure, (200, THREAT_LOGS)])
    client, _ = make_client(http, STATIC_CREDS)
    with pytest.raises(error):
        client.op(SYSTEM_INFO_CMD)

    # The firewall is not asked again in the same run: a hung firewall costs one timeout, not one per call.
    with pytest.raises(PanosSkipped):
        call(client)
    assert len(http.calls) == 1

    client.start_run()
    call(client)
    assert len(http.calls) == 2


def test_stream_that_breaks_mid_way_makes_the_next_calls_fail_fast():
    first_entry_end = THREAT_LOGS.index(b'</entry>') + len(b'</entry>')

    class BrokenRaw:
        def stream(self, *_args, **_kwargs):
            yield THREAT_LOGS[:first_entry_end]
            raise ProtocolError('connection broken')

        def close(self):
            pass

    resp = response(200, b'')
    resp.raw = BrokenRaw()
    http = FakeHttp(api=[resp, (200, SYSTEM_INFO)])
    client, _ = make_client(http, STATIC_CREDS)

    seqnos = []
    with pytest.raises(PanosUnreachable):
        client.read_log_job('2', lambda entry: seqnos.append(entry.findtext('seqno')))

    assert len(seqnos) == 1 and seqnos[0]
    assert client.stats.unreachable
    with pytest.raises(PanosSkipped):
        client.op(SYSTEM_INFO_CMD)
    assert len(http.calls) == 1
    # The call itself was answered: can_connect does not turn to 0 because the body broke.
    stats = client.stats
    assert (stats.calls, stats.answered) == (1, True)


def test_failing_entry_callback_releases_the_slot_and_counts_the_call():
    http = FakeHttp(api=[(200, THREAT_LOGS), (200, SYSTEM_INFO)])
    keys = KeyManager(http, HOST, STATIC_CREDS)
    # One slot: a call left holding it would block the next one forever.
    client = PanosClient(http, HOST, keys, logging.getLogger('test_api'), max_in_flight=1)

    def broken(_entry):
        raise RuntimeError('collector bug')

    with pytest.raises(RuntimeError):
        client.read_log_job('2', broken)
    client.op(SYSTEM_INFO_CMD)

    stats = client.stats
    assert (stats.calls, stats.answered) == (2, True)


class ConcurrencyProbe:
    """Transport that blocks every call until released and records the peak number of calls in flight."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0
        self.entered = threading.Semaphore(0)
        self.release = threading.Event()

    def post(self, url: str, **options: Any) -> MockResponse:
        with self.lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
        self.entered.release()
        self.release.wait(timeout=5)
        with self.lock:
            self.in_flight -= 1
        return response(200, SYSTEM_INFO)


def test_at_most_two_calls_in_flight():
    probe = ConcurrencyProbe()
    client, _ = make_client(probe, STATIC_CREDS)
    threads = [threading.Thread(target=client.op, args=(SYSTEM_INFO_CMD,)) for _ in range(3)]

    for thread in threads:
        thread.start()
    assert probe.entered.acquire(timeout=5)
    assert probe.entered.acquire(timeout=5)
    # Two calls are blocked in the transport; the third thread must be waiting for a slot.
    assert not probe.entered.acquire(timeout=0.2)
    probe.release.set()
    for thread in threads:
        thread.join(timeout=5)

    assert probe.peak == 2
    assert probe.entered.acquire(timeout=5)
