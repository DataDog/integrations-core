# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import io
import logging
import threading
from typing import Any

import pytest
import requests
from urllib3.exceptions import ProtocolError

from datadog_checks.pan_firewall.api import (
    PanosApiError,
    PanosAuthError,
    PanosClient,
    PanosConnectionError,
    PanosError,
    PanosSkipped,
    PanosTimeout,
    api_url,
)
from datadog_checks.pan_firewall.auth import Credentials, KeyManager

from .common import FIXTURES
from .fixture_map import op_fixture

HOST = '192.0.2.10'
PORT = 443
URL = f'https://{HOST}:{PORT}/api/'
SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
GENERATED_KEY = 'GENERATED-KEY-0123456789'
STATIC_KEY = 'STATIC-KEY-9876543210'
PASSWORD_CREDS = Credentials(username='dummy-user', password='s3cret-pw', api_key=None)
STATIC_CREDS = Credentials(username=None, password=None, api_key=STATIC_KEY)

SYSTEM_INFO = op_fixture(SYSTEM_INFO_CMD).read_bytes()
THREAT_SUBMIT = (FIXTURES / 'fw-a' / 'threat_log_5m_submit.xml').read_bytes()
THREAT_LOGS = (FIXTURES / 'fw-a' / 'threat_log_5m.xml').read_bytes()
INVALID_CREDENTIAL = (FIXTURES / 'synthetic' / 'auth_invalid_credential.xml').read_bytes()
NOT_AUTHENTICATED = (FIXTURES / 'synthetic' / 'auth_not_authenticated.xml').read_bytes()
CODE_16 = (FIXTURES / 'synthetic' / 'auth_code_16.xml').read_bytes()

# The keygen success shape (`result/key`) from the PAN-OS XML API docs. Kept inline: fixture files must hold no key.
KEYGEN_OK = f'<response status="success"><result><key>{GENERATED_KEY}</key></result></response>'.encode()

# Auth rejections the client must treat as an expired key, with the HTTP status they arrive with.
AUTH_FAILURES = [
    pytest.param(403, INVALID_CREDENTIAL, id='http-403-invalid-credential'),
    pytest.param(403, NOT_AUTHENTICATED, id='http-403-not-authenticated'),
    pytest.param(200, INVALID_CREDENTIAL, id='code-403-in-body'),
    pytest.param(200, CODE_16, id='code-16'),
]

type Answer = tuple[int, bytes] | Exception | requests.Response


def make_response(status: int, body: bytes) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp.raw = io.BytesIO(body)
    resp.url = URL
    return resp


class FakeHttp:
    """Stands in for `RequestsWrapper`: records every `post` and answers keygen and API calls from two queues."""

    def __init__(self, keygen: list[Answer] | None = None, api: list[Answer] | None = None):
        self.keygen = list(keygen or [])
        self.api = list(api or [])
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **options: Any) -> requests.Response:
        self.calls.append({'url': url, **options})
        queue = self.keygen if options['data'].get('type') == 'keygen' else self.api
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, requests.Response):
            return answer
        return make_response(*answer)

    def calls_of(self, kind: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if (c['data'].get('type') == 'keygen') == (kind == 'keygen')]


def make_client(http: Any, creds: Credentials = PASSWORD_CREDS, log: Any = None) -> tuple[PanosClient, KeyManager]:
    keys = KeyManager(http, api_url(HOST, PORT), creds)
    return PanosClient(http, HOST, PORT, keys, log or logging.getLogger('test_api'), max_in_flight=2), keys


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
        keygen=[(200, KEYGEN_OK), (200, KEYGEN_OK)],
        api=[
            (200, SYSTEM_INFO),
            (200, THREAT_SUBMIT),
            (200, THREAT_LOGS),
            (200, THREAT_LOGS),
            (403, INVALID_CREDENTIAL),
            (403, INVALID_CREDENTIAL),
            requests.exceptions.ConnectionError('refused'),
        ],
    )
    client, keys = make_client(http)
    errors = []

    client.op(SYSTEM_INFO_CMD)
    client.submit_job({'type': 'log', 'log-type': 'threat'})
    client.get_job('log', '2')
    with client.open_log_job('2') as (_, entries):
        list(entries)
    for _ in range(2):
        try:
            client.op(SYSTEM_INFO_CMD)
        except PanosError as e:
            errors.append(e)

    assert [type(e) for e in errors] == [PanosAuthError, PanosConnectionError]
    for call in http.calls:
        sent = ' '.join([call['url'], *call['data'].keys(), *call['data'].values()])
        assert GENERATED_KEY not in sent
        assert 'key=' not in call['url']
    for text in [caplog.text, repr(keys), repr(PASSWORD_CREDS), repr(STATIC_CREDS)]:
        for secret in (GENERATED_KEY, STATIC_KEY, 's3cret-pw'):
            assert secret not in text
    for error in errors:
        assert GENERATED_KEY not in str(error)
        assert GENERATED_KEY not in repr(error)


@pytest.mark.parametrize('status, body', AUTH_FAILURES)
def test_rejected_key_is_regenerated_once_and_the_call_retried(status, body):
    http = FakeHttp(keygen=[(200, KEYGEN_OK), (200, KEYGEN_OK)], api=[(status, body), (200, SYSTEM_INFO)])
    client, keys = make_client(http)

    root = client.op(SYSTEM_INFO_CMD)

    assert root.findtext('./result/system/hostname') == 'fw-a'
    assert len(http.calls_of('keygen')) == 2
    assert len(http.calls_of('api')) == 2
    assert keys.auth_failed is False


@pytest.mark.parametrize('status, body', AUTH_FAILURES)
def test_key_rejected_again_after_regeneration_raises(status, body):
    http = FakeHttp(keygen=[(200, KEYGEN_OK), (200, KEYGEN_OK)], api=[(status, body), (status, body)])
    client, _ = make_client(http)

    with pytest.raises(PanosAuthError):
        client.op(SYSTEM_INFO_CMD)

    assert len(http.calls_of('keygen')) == 2
    assert len(http.calls_of('api')) == 2


def test_log_stream_regenerates_a_rejected_key():
    http = FakeHttp(keygen=[(200, KEYGEN_OK), (200, KEYGEN_OK)], api=[(200, CODE_16), (200, THREAT_LOGS)])
    client, _ = make_client(http)

    with client.open_log_job('2') as (status, entries):
        seqnos = [entry.findtext('seqno') for entry in entries]

    assert status == 'FIN'
    assert len(seqnos) == 39
    assert seqnos[0] == '7691899338913481002'
    assert seqnos[-1] == '7691899338913480957'
    assert http.calls_of('api')[-1]['data'] == {'type': 'log', 'action': 'get', 'job-id': '2'}
    assert http.calls_of('api')[-1]['stream'] is True
    assert len(http.calls_of('keygen')) == 2


def test_keygen_rejection_marks_credentials_invalid_without_retry():
    http = FakeHttp(keygen=[(403, INVALID_CREDENTIAL)])
    client, keys = make_client(http)

    with pytest.raises(PanosAuthError):
        client.op(SYSTEM_INFO_CMD)

    assert keys.auth_failed is True
    assert len(http.calls_of('keygen')) == 1
    assert http.calls_of('api') == []


def test_rejected_keygen_is_not_retried_until_reset():
    http = FakeHttp(
        keygen=[(200, KEYGEN_OK), (403, INVALID_CREDENTIAL), (200, KEYGEN_OK)],
        api=[(403, INVALID_CREDENTIAL), (200, SYSTEM_INFO)],
    )
    client, keys = make_client(http)

    # The key is revoked and the credentials changed mid-run: the renewal keygen is rejected, and the later
    # call of the same run (or a second call in flight with the same key) must not log in again.
    for _ in range(2):
        with pytest.raises(PanosAuthError):
            client.op(SYSTEM_INFO_CMD)
    assert len(http.calls_of('keygen')) == 2
    assert keys.auth_failed is True

    keys.reset_failure()
    client.op(SYSTEM_INFO_CMD)

    assert len(http.calls_of('keygen')) == 3
    assert keys.auth_failed is False


def test_non_panos_http_403_is_not_an_auth_failure():
    # A proxy's 403 page says nothing about the PAN-OS key or credentials: no renewal, no invalid-credentials state.
    http = FakeHttp(keygen=[(200, KEYGEN_OK)], api=[(403, b'<html><body>403 Forbidden</body></html>')])
    client, keys = make_client(http)

    with pytest.raises(PanosApiError) as exc_info:
        client.op(SYSTEM_INFO_CMD)

    assert not isinstance(exc_info.value, PanosAuthError)
    assert exc_info.value.code == '403'
    assert len(http.calls_of('keygen')) == 1
    assert keys.auth_failed is False


def test_static_key_is_never_regenerated():
    http = FakeHttp(api=[(403, INVALID_CREDENTIAL)])
    client, keys = make_client(http, STATIC_CREDS)

    with pytest.raises(PanosAuthError):
        client.op(SYSTEM_INFO_CMD)

    assert keys.auth_failed is True
    assert http.calls_of('keygen') == []
    assert http.calls[0]['extra_headers'] == {'X-PAN-KEY': STATIC_KEY}


@pytest.mark.parametrize(
    'raised, expected, message',
    [
        pytest.param(requests.exceptions.ReadTimeout('read timed out'), PanosTimeout, 'timed out', id='timeout'),
        pytest.param(
            requests.exceptions.ConnectionError('connection refused'),
            PanosConnectionError,
            'cannot connect',
            id='refused',
        ),
        pytest.param(
            requests.exceptions.SSLError('certificate verify failed'), PanosConnectionError, 'TLS error', id='tls'
        ),
    ],
)
def test_transport_errors_are_typed_and_name_the_host(raised, expected, message):
    http = FakeHttp(api=[raised])
    client, _ = make_client(http, STATIC_CREDS)

    with pytest.raises(expected) as exc_info:
        client.op(SYSTEM_INFO_CMD)

    assert type(exc_info.value) is expected
    assert message in str(exc_info.value)
    assert HOST in str(exc_info.value)


def read_log_job(client, job_id):
    with client.open_log_job(job_id) as (_, entries):
        return list(entries)


@pytest.mark.parametrize(
    'call',
    [
        pytest.param(lambda client: client.op(SYSTEM_INFO_CMD), id='op'),
        pytest.param(lambda client: read_log_job(client, '2'), id='log-job'),
    ],
)
@pytest.mark.parametrize(
    'failure, error',
    [
        pytest.param(requests.exceptions.ReadTimeout('read timed out'), PanosTimeout, id='timeout'),
        pytest.param(requests.exceptions.ConnectionError('refused'), PanosConnectionError, id='refused'),
    ],
)
def test_calls_after_a_timeout_or_refusal_fail_fast_until_the_stats_are_taken(call, failure, error):
    http = FakeHttp(api=[failure, (200, THREAT_LOGS)])
    client, _ = make_client(http, STATIC_CREDS)
    with pytest.raises(error):
        client.op(SYSTEM_INFO_CMD)

    # The firewall is not asked again in the same run: a hung firewall costs one timeout, not one per call.
    with pytest.raises(PanosSkipped):
        call(client)
    assert len(http.calls) == 1

    client.take_stats()
    call(client)
    assert len(http.calls) == 2


def test_jobs_return_the_job_id_and_status():
    http = FakeHttp(api=[(200, THREAT_SUBMIT), (200, THREAT_LOGS)])
    client, _ = make_client(http, STATIC_CREDS)

    job_id = client.submit_job({'type': 'log', 'log-type': 'threat', 'nlogs': '5000'})
    status, root = client.get_job('log', job_id)

    assert job_id == '2'
    assert status == 'FIN'
    assert root.find('./result/log/logs') is not None
    assert http.calls[0]['data'] == {'type': 'log', 'log-type': 'threat', 'nlogs': '5000'}
    assert http.calls[1]['data'] == {'type': 'log', 'action': 'get', 'job-id': '2'}


def test_open_log_job_reads_status_and_streams_the_entries_in_one_request():
    http = FakeHttp(api=[(200, THREAT_LOGS)])
    client, _ = make_client(http, STATIC_CREDS)

    with client.open_log_job('2') as (status, entries):
        seqnos = [entry.findtext('seqno') for entry in entries]

    assert status == 'FIN'
    assert len(seqnos) == 39
    assert len(http.calls) == 1
    assert http.calls[0]['stream'] is True


def test_stream_that_breaks_mid_way_makes_the_next_calls_fail_fast():
    first_entry_end = THREAT_LOGS.index(b'</entry>') + len(b'</entry>')

    class BrokenRaw:
        def stream(self, *_args, **_kwargs):
            yield THREAT_LOGS[:first_entry_end]
            raise ProtocolError('connection broken')

        def close(self):
            pass

    resp = make_response(200, b'')
    resp.raw = BrokenRaw()
    http = FakeHttp(api=[resp, (200, SYSTEM_INFO)])
    client, _ = make_client(http, STATIC_CREDS)

    with pytest.raises(PanosConnectionError), client.open_log_job('2') as (_, entries):
        assert next(entries).findtext('seqno')
        next(entries)

    assert client.unreachable
    with pytest.raises(PanosSkipped):
        client.op(SYSTEM_INFO_CMD)
    assert len(http.calls) == 1
    # The call itself was answered: can_connect does not turn to 0 because the body broke.
    stats = client.take_stats()
    assert (stats.calls, stats.answered) == (1, True)


def test_open_log_job_that_is_not_finished_yields_no_entries():
    running = (FIXTURES / 'synthetic' / 'threat_log_act.xml').read_bytes()
    http = FakeHttp(api=[(200, running)])
    client, _ = make_client(http, STATIC_CREDS)

    with client.open_log_job('93') as (status, entries):
        assert status == 'ACT'
        assert list(entries) == []


def test_api_error_is_not_treated_as_auth_failure():
    body = (FIXTURES / 'fw-a-probe' / 'report_top-rules.xml').read_bytes()
    http = FakeHttp(api=[(200, body)])
    client, keys = make_client(http, STATIC_CREDS)

    with pytest.raises(PanosApiError) as exc_info:
        client.op(SYSTEM_INFO_CMD)

    assert type(exc_info.value) is PanosApiError
    assert exc_info.value.code == '400'
    assert keys.auth_failed is False


class ConcurrencyProbe:
    """Transport that blocks every call until released and records the peak number of calls in flight."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0
        self.entered = threading.Semaphore(0)
        self.release = threading.Event()

    def post(self, url: str, **options: Any) -> requests.Response:
        with self.lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
        self.entered.release()
        self.release.wait(timeout=5)
        with self.lock:
            self.in_flight -= 1
        return make_response(200, SYSTEM_INFO)


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
