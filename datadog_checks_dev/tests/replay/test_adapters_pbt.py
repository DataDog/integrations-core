# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property-based tests for replay adapter contracts.

These tests exercise the replay harness itself, not any particular integration.
They generate small synthetic fixture records for each adapter and assert the
core adapter contract: valid records round-trip through monkeypatched calls,
wrong operations fail clearly, and exhausted fixtures do not silently produce
extra data.
"""

import json
import sys
import types
from typing import Any

import pytest
import requests
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from datadog_checks.base.utils import subprocess_output
from datadog_checks.dev.replay.adapters.process import install_replay_process_state
from datadog_checks.dev.replay.adapters.psycopg import install_replay_psycopg
from datadog_checks.dev.replay.adapters.requests import build_get_record, install_replay_session_get
from datadog_checks.dev.replay.adapters.subprocess import install_replay_get_subprocess_output
from datadog_checks.dev.replay.adapters.tcp import install_replay_tcp_clients

safe_text = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters=['\x00']),
    max_size=200,
)
non_empty_safe_text = safe_text.filter(bool)
urls = st.from_regex(r'https?://example\.test/[A-Za-z0-9/_-]{1,40}', fullmatch=True)
headers = st.dictionaries(non_empty_safe_text, safe_text, min_size=1, max_size=5)
optional_headers = st.one_of(st.none(), headers)
argvs = st.lists(safe_text, max_size=5).map(list)


pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])


@pbt_settings
@given(url=urls, body=safe_text, status=st.integers(min_value=100, max_value=599), headers=optional_headers)
def test_requests_replay_round_trips_response(monkeypatch, tmp_path, url, body, status, headers):
    fixture_path = tmp_path / 'capture.json'
    record = build_get_record(url, body, status=status, headers=headers)
    fixture_path.write_text(json.dumps([record]) + '\n')

    install_replay_session_get(monkeypatch, fixture_path)

    response = requests.Session().get(url)

    assert response.status_code == status
    assert response.text == body
    assert response.content == body.encode('utf-8')
    assert dict(response.headers) == record['headers']
    assert response.ok is (status < 400)


def test_requests_replay_response_json_decodes_body(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    record = build_get_record('http://example.test/json', '{"version": "1.2.3"}')
    fixture_path.write_text(json.dumps([record]) + '\n')

    install_replay_session_get(monkeypatch, fixture_path)

    assert requests.Session().get('http://example.test/json').json() == {'version': '1.2.3'}


@pbt_settings
@given(url_a=urls, url_b=urls)
def test_requests_replay_rejects_wrong_url(monkeypatch, tmp_path, url_a, url_b):
    assume(url_a != url_b)
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record(url_a, 'body')]) + '\n')

    install_replay_session_get(monkeypatch, fixture_path)

    with pytest.raises(AssertionError, match='does not match'):
        requests.Session().get(url_b)


@pbt_settings
@given(url=urls, body=safe_text)
def test_requests_replay_rejects_exhausted_records(monkeypatch, tmp_path, url, body):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record(url, body)]) + '\n')

    install_replay_session_get(monkeypatch, fixture_path)

    requests.Session().get(url)
    with pytest.raises(AssertionError, match='No recorded HTTP response'):
        requests.Session().get(url)


@pbt_settings
@given(argv=argvs, stdout=safe_text, stderr=safe_text, returncode=st.integers(min_value=0, max_value=255))
def test_subprocess_replay_round_trips_success(monkeypatch, tmp_path, argv, stdout, stderr, returncode):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'argv': argv,
                    'stdout': stdout,
                    'stderr': stderr,
                    'returncode': returncode,
                    'exception': None,
                }
            ]
        )
        + '\n'
    )

    install_replay_get_subprocess_output(monkeypatch, fixture_path)

    assert subprocess_output.get_subprocess_output(argv, None) == (stdout, stderr, returncode)


@pbt_settings
@given(argv_a=argvs, argv_b=argvs)
def test_subprocess_replay_rejects_wrong_argv(monkeypatch, tmp_path, argv_a, argv_b):
    assume(argv_a != argv_b)
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'argv': argv_a,
                    'stdout': 'stdout',
                    'stderr': 'stderr',
                    'returncode': 0,
                    'exception': None,
                }
            ]
        )
        + '\n'
    )

    install_replay_get_subprocess_output(monkeypatch, fixture_path)

    with pytest.raises(AssertionError, match='does not match'):
        subprocess_output.get_subprocess_output(argv_b, None)


@pbt_settings
@given(argv=argvs, stdout=safe_text, stderr=safe_text, returncode=st.integers(min_value=0, max_value=255))
def test_subprocess_replay_rejects_exhausted_records(monkeypatch, tmp_path, argv, stdout, stderr, returncode):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'argv': argv,
                    'stdout': stdout,
                    'stderr': stderr,
                    'returncode': returncode,
                    'exception': None,
                }
            ]
        )
        + '\n'
    )

    install_replay_get_subprocess_output(monkeypatch, fixture_path)

    subprocess_output.get_subprocess_output(argv, None)
    with pytest.raises(AssertionError, match='No recorded subprocess output'):
        subprocess_output.get_subprocess_output(argv, None)


@pbt_settings
@given(
    argv=argvs,
    exception_type=st.sampled_from(['OSError', 'ValueError', 'RuntimeError']),
    message=non_empty_safe_text,
)
def test_subprocess_replay_round_trips_supported_exceptions(monkeypatch, tmp_path, argv, exception_type, message):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'argv': argv,
                    'stdout': None,
                    'stderr': None,
                    'returncode': None,
                    'exception': {
                        'type': exception_type,
                        'module': 'builtins',
                        'message': message,
                    },
                }
            ]
        )
        + '\n'
    )

    install_replay_get_subprocess_output(monkeypatch, fixture_path)

    expected_exception = {'OSError': OSError, 'ValueError': ValueError, 'RuntimeError': RuntimeError}[exception_type]
    with pytest.raises(expected_exception, match='.*') as exc_info:
        subprocess_output.get_subprocess_output(argv, None)

    assert str(exc_info.value) == message


@pbt_settings
@given(
    host=non_empty_safe_text,
    port=st.integers(min_value=1, max_value=65535),
    payload=st.binary(max_size=200),
    response=st.binary(max_size=200),
)
def test_tcp_socket_replay_round_trips_send_and_recv(monkeypatch, tmp_path, host, port, payload, response):
    import base64
    import socket

    fixture_path = tmp_path / 'capture.json'
    bufsize = max(1, len(response))
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'operation': 'socket.create_connection',
                    'address': [host, port],
                    'timeout': None,
                    'source_address': None,
                    'exception': None,
                },
                {
                    'operation': 'socket.sendall',
                    'data_b64': base64.b64encode(payload).decode('ascii'),
                    'exception': None,
                },
                {
                    'operation': 'socket.recv',
                    'bufsize': bufsize,
                    'data_b64': base64.b64encode(response).decode('ascii'),
                    'exception': None,
                },
                {'operation': 'socket.close', 'exception': None},
            ]
        )
        + '\n'
    )

    install_replay_tcp_clients(monkeypatch, fixture_path)

    with socket.create_connection((host, port)) as sock:
        sock.sendall(payload)
        assert sock.recv(bufsize) == response


@pbt_settings
@given(
    host_a=non_empty_safe_text,
    port_a=st.integers(min_value=1, max_value=65535),
    host_b=non_empty_safe_text,
    port_b=st.integers(min_value=1, max_value=65535),
)
def test_tcp_socket_replay_rejects_wrong_connection(monkeypatch, tmp_path, host_a, port_a, host_b, port_b):
    import socket

    assume((host_a, port_a) != (host_b, port_b))
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'operation': 'socket.create_connection',
                    'address': [host_a, port_a],
                    'timeout': None,
                    'source_address': None,
                    'exception': None,
                }
            ]
        )
        + '\n'
    )

    install_replay_tcp_clients(monkeypatch, fixture_path)

    with pytest.raises(AssertionError, match='does not match'):
        socket.create_connection((host_b, port_b))


@pbt_settings
@given(host=non_empty_safe_text, port=st.integers(min_value=1, max_value=65535))
def test_tcp_socket_replay_rejects_exhausted_connections(monkeypatch, tmp_path, host, port):
    import socket

    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'operation': 'socket.create_connection',
                    'address': [host, port],
                    'timeout': None,
                    'source_address': None,
                    'exception': None,
                }
            ]
        )
        + '\n'
    )

    install_replay_tcp_clients(monkeypatch, fixture_path)

    socket.create_connection((host, port))
    with pytest.raises(AssertionError, match='No recorded TCP socket connection'):
        socket.create_connection((host, port))


@pbt_settings
@given(pid=st.integers(min_value=1, max_value=100000), cmdline=st.lists(safe_text, max_size=5))
def test_process_replay_round_trips_process_state(monkeypatch, tmp_path, pid, cmdline):
    fake_psutil: Any = types.ModuleType('psutil')
    fake_psutil.NoSuchProcess = type('NoSuchProcess', (Exception,), {})
    fake_psutil.AccessDenied = type('AccessDenied', (Exception,), {})
    fake_psutil.process_iter = lambda: []
    monkeypatch.setitem(sys.modules, 'psutil', fake_psutil)

    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {'operation': 'psutil.process_iter', 'result': [pid], 'exception': None},
                {'operation': 'psutil.Process.cmdline', 'pid': pid, 'result': cmdline, 'exception': None},
                {'operation': 'psutil.Process.children', 'pid': pid, 'result': [], 'exception': None},
            ]
        )
        + '\n'
    )

    install_replay_process_state(monkeypatch, fixture_path)

    processes = list(fake_psutil.process_iter())
    assert len(processes) == 1
    assert processes[0].pid == pid
    assert processes[0].cmdline() == cmdline
    assert processes[0].children() == []


@pbt_settings
@given(
    sql=non_empty_safe_text,
    params=st.one_of(st.none(), safe_text, st.integers(), st.lists(safe_text, max_size=3)),
    rows=st.lists(
        st.dictionaries(non_empty_safe_text, st.one_of(safe_text, st.integers(), st.none()), max_size=3), max_size=5
    ),
)
def test_psycopg_replay_round_trips_query_rows(monkeypatch, tmp_path, sql, params, rows):
    class FakeConnection:
        pass

    fake_pg: Any = types.ModuleType('psycopg')
    fake_pg.ProgrammingError = type('ProgrammingError', (Exception,), {})
    fake_pg.OperationalError = type('OperationalError', (Exception,), {})
    fake_pg.InterfaceError = type('InterfaceError', (Exception,), {})
    fake_pg.Error = type('Error', (Exception,), {})
    fake_pg.connect = lambda *args, **kwargs: FakeConnection()
    monkeypatch.setitem(sys.modules, 'psycopg', fake_pg)

    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'operation': 'psycopg.connect',
                    'args': [],
                    'kwargs': {'host': 'localhost', 'password': '******'},
                    'exception': None,
                },
                {
                    'operation': 'psycopg.cursor.execute',
                    'sql': sql,
                    'params': params,
                    'cursor_args': [],
                    'row_factory': None,
                    'rows': rows,
                    'exception': None,
                },
            ]
        )
        + '\n'
    )

    install_replay_psycopg(monkeypatch, fixture_path)

    connection: Any = fake_pg.connect(host='localhost', password='secret')
    cursor = connection.cursor()
    cursor.execute(sql, params)
    assert list(cursor) == rows


def test_adapter_env_var_can_disable_tcp(monkeypatch, tmp_path):
    from datadog_checks.dev.replay.adapters import install_replay_adapters

    fixture = tmp_path / 'capture.json'
    fixture.write_text(
        json.dumps(
            {
                'version': 2,
                'readings': 1,
                'adapters': ['requests', 'tcp'],
                'files': {'requests': 'capture.requests.json', 'tcp': 'capture.tcp.json'},
                'counts': {'requests': 1, 'tcp': 1},
            }
        )
    )
    (tmp_path / 'capture.requests.json').write_text('[]')
    (tmp_path / 'capture.tcp.json').write_text('[]')

    monkeypatch.setenv('DD_REPLAY_ADAPTERS', 'requests')

    installed = install_replay_adapters(monkeypatch, 'replay', fixture, 'example')

    assert set(installed) == {'requests'}
