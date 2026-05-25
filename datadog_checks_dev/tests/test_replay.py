# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import socket
import sys
import types

import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils import subprocess_output
from datadog_checks.dev.replay.adapters import install_replay_adapters, write_fixture_manifest
from datadog_checks.dev.replay.adapters.process import (
    install_live_recording_process_state,
    install_replay_process_state,
)
from datadog_checks.dev.replay.adapters.psycopg import install_live_recording_psycopg, install_replay_psycopg
from datadog_checks.dev.replay.adapters.requests import build_get_record, install_replay_session_get
from datadog_checks.dev.replay.adapters.subprocess import (
    install_live_recording_get_subprocess_output,
    install_replay_get_subprocess_output,
)
from datadog_checks.dev.replay.adapters.tcp import install_live_recording_tcp_clients, install_replay_tcp_clients
from datadog_checks.dev.replay.diff import diff_outputs
from datadog_checks.dev.replay.normalize import normalize_output
from datadog_checks.dev.replay.output import serialize_aggregator
from datadog_checks.dev.replay.pytest import infer_check_class


class ExampleCheck(AgentCheck):
    def check(self, instance):
        pass


class AgentOutputReplayCheck(AgentCheck):
    __NAMESPACE__ = 'agent_output_replay'

    def check(self, instance):
        self.gauge('metric', 1, tags=['b:2', 'a:1'])
        self.set_metadata('version.raw', '1.2.3')
        self.set_external_tags([('external.example', {'src': ['z:9', 'a:1']})])
        self.write_persistent_cache('cursor', 'abc')
        self.send_log({'message': 'hello'}, cursor={'offset': 2}, stream='default')
        from datadog_checks.base.agent import datadog_agent

        datadog_agent.set_check_metadata(self.check_id, 'flavor', {'name': 'example'})
        datadog_agent.emit_agent_telemetry(self.name, 'telemetry.metric', 7, 'gauge')


def test_infer_check_class_from_module_exports(monkeypatch):
    module = types.ModuleType('datadog_checks.example_replay')
    module.__all__ = ['__version__', 'ExampleCheck']
    module.__version__ = '1.0.0'
    module.ExampleCheck = ExampleCheck
    monkeypatch.setitem(sys.modules, 'datadog_checks.example_replay', module)

    assert infer_check_class('example_replay') is ExampleCheck


def test_normalize_output_sorts_metrics_and_tags():
    output = {
        'metrics': [
            {'name': 'z.metric', 'type': 0, 'value': 2, 'tags': ['b:2', 'a:1'], 'hostname': '', 'device': None},
            {'name': 'a.metric', 'type': 0, 'value': 1, 'tags': ['z:9'], 'hostname': '', 'device': None},
        ],
        'service_checks': [],
        'events': [],
        'event_platform_events': {},
    }

    normalized = normalize_output(output)

    assert [metric['name'] for metric in normalized['metrics']] == ['a.metric', 'z.metric']
    assert normalized['metrics'][1]['tags'] == ['a:1', 'b:2']


def test_diff_outputs_reports_added_and_removed_metric_records():
    old = {
        'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1, 'tags': ['a:1']}],
        'service_checks': [],
        'events': [],
    }
    new = {
        'metrics': [{'name': 'example.metric', 'type': 0, 'value': 2, 'tags': ['a:1']}],
        'service_checks': [],
        'events': [],
    }

    diff = diff_outputs(old, new)

    assert diff['changed'] is True
    assert diff['collections']['metrics']['removed'] == old['metrics']
    assert diff['collections']['metrics']['added'] == new['metrics']


def test_requests_replay_fixture_miss_on_wrong_url(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record('http://example.test/metrics', 'metric 1\n')]) + '\n')
    install_replay_session_get(monkeypatch, fixture_path)

    with pytest.raises(AssertionError, match='does not match'):
        requests.Session().get('http://example.test/other')


def test_requests_replay_fixture_miss_when_records_exhausted(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record('http://example.test/metrics', 'metric 1\n')]) + '\n')
    install_replay_session_get(monkeypatch, fixture_path)

    requests.Session().get('http://example.test/metrics')
    with pytest.raises(AssertionError, match='No recorded HTTP response'):
        requests.Session().get('http://example.test/metrics')


def test_install_replay_adapters_dispatches_requests_replay(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    request_fixture = tmp_path / 'capture.requests.json'
    request_fixture.write_text(json.dumps([build_get_record('http://example.test/metrics', 'metric 1\n')]) + '\n')
    write_fixture_manifest(fixture_path, {'requests': []})

    install_replay_adapters(monkeypatch, 'replay', fixture_path)

    response = requests.Session().get('http://example.test/metrics')
    assert response.text == 'metric 1\n'


def test_subprocess_record_and_replay(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'

    def fake_get_subprocess_output(cmd, log, *args, **kwargs):
        return 'stdout', 'stderr', 0

    monkeypatch.setattr(subprocess_output, 'get_subprocess_output', fake_get_subprocess_output)
    install_live_recording_get_subprocess_output(monkeypatch, fixture_path)

    assert subprocess_output.get_subprocess_output(['example', 'command'], None) == ('stdout', 'stderr', 0)

    install_replay_get_subprocess_output(monkeypatch, fixture_path)
    assert subprocess_output.get_subprocess_output(['example', 'command'], None) == ('stdout', 'stderr', 0)


def test_subprocess_replay_fixture_miss_on_wrong_command(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'argv': ['expected'],
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
        subprocess_output.get_subprocess_output(['actual'], None)


def test_subprocess_record_and_replay_exception(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'

    def fake_get_subprocess_output(cmd, log, *args, **kwargs):
        raise OSError('boom')

    monkeypatch.setattr(subprocess_output, 'get_subprocess_output', fake_get_subprocess_output)
    install_live_recording_get_subprocess_output(monkeypatch, fixture_path)

    with pytest.raises(OSError, match='boom'):
        subprocess_output.get_subprocess_output(['example'], None)

    install_replay_get_subprocess_output(monkeypatch, fixture_path)
    with pytest.raises(OSError, match='boom'):
        subprocess_output.get_subprocess_output(['example'], None)


def test_tcp_socket_record_and_replay(monkeypatch, tmp_path):
    class FakeSocket:
        def __init__(self):
            self._responses = [b'imok', b'']

        def settimeout(self, timeout):
            self.timeout = timeout

        def sendall(self, data):
            self.sent = data

        def recv(self, bufsize):
            return self._responses.pop(0)

        def close(self):
            self.closed = True

    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs: FakeSocket())

    fixture_path = tmp_path / 'capture.json'
    install_live_recording_tcp_clients(monkeypatch, fixture_path)

    sock = socket.create_connection(('localhost', 2181))
    sock.settimeout(3.0)
    sock.sendall(b'ruok\n')
    assert sock.recv(1024) == b'imok'
    assert sock.recv(1024) == b''
    sock.close()

    install_replay_tcp_clients(monkeypatch, fixture_path)
    sock = socket.create_connection(('localhost', 2181))
    sock.settimeout(3.0)
    sock.sendall(b'ruok\n')
    assert sock.recv(1024) == b'imok'
    assert sock.recv(1024) == b''
    sock.close()


def test_tcp_replay_fixture_miss_on_wrong_send(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(
        json.dumps(
            [
                {
                    'operation': 'socket.create_connection',
                    'address': ['localhost', 2181],
                    'timeout': None,
                    'source_address': None,
                    'exception': None,
                },
                {'operation': 'socket.sendall', 'data_b64': 'cnVvawo=', 'exception': None},
            ]
        )
        + '\n'
    )
    install_replay_tcp_clients(monkeypatch, fixture_path)

    sock = socket.create_connection(('localhost', 2181))
    with pytest.raises(AssertionError, match='does not match'):
        sock.sendall(b'stat\n')


def test_process_record_and_replay(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'

    class FakeProcess:
        def __init__(self, pid, cmdline=None, children=None, cpu_times=None):
            self.pid = pid
            self._cmdline = cmdline or []
            self._children = children or []
            self._cpu_times = list(cpu_times or [])

        def cmdline(self):
            return self._cmdline

        def children(self):
            return self._children

        def cpu_times(self):
            return self._cpu_times.pop(0)

    child = FakeProcess(2, cpu_times=[(1.0, 0.0), (1.5, 0.0)])
    master = FakeProcess(1, ['gunicorn: master [example]'], [child])
    fake_psutil = types.ModuleType('psutil')
    fake_psutil.NoSuchProcess = type('NoSuchProcess', (Exception,), {})
    fake_psutil.AccessDenied = type('AccessDenied', (Exception,), {})
    fake_psutil.process_iter = lambda: [master]
    monkeypatch.setitem(sys.modules, 'psutil', fake_psutil)
    install_live_recording_process_state(monkeypatch, fixture_path)

    processes = list(fake_psutil.process_iter())
    assert processes[0].cmdline() == ['gunicorn: master [example]']
    workers = processes[0].children()
    assert workers[0].cpu_times() == [1.0, 0.0]
    assert workers[0].cpu_times() == [1.5, 0.0]

    install_replay_process_state(monkeypatch, fixture_path)
    processes = list(fake_psutil.process_iter())
    assert processes[0].cmdline() == ['gunicorn: master [example]']
    workers = processes[0].children()
    assert workers[0].cpu_times() == [1.0, 0.0]
    assert workers[0].cpu_times() == [1.5, 0.0]


def test_psycopg_record_and_replay(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'

    class FakeCursor:
        def __init__(self, rows):
            self._rows = rows

        def execute(self, sql, params=None, *args, **kwargs):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return self._rows

        def close(self):
            pass

    class FakeConnection:
        def cursor(self, *args, **kwargs):
            return FakeCursor([{'database': 'example', 'avg_recv': 1}])

        def close(self):
            pass

    fake_pg = types.ModuleType('psycopg')
    fake_pg.ProgrammingError = type('ProgrammingError', (Exception,), {})
    fake_pg.OperationalError = type('OperationalError', (Exception,), {})
    fake_pg.InterfaceError = type('InterfaceError', (Exception,), {})
    fake_pg.Error = type('Error', (Exception,), {})
    fake_pg.connect = lambda *args, **kwargs: FakeConnection()
    monkeypatch.setitem(sys.modules, 'psycopg', fake_pg)

    install_live_recording_psycopg(monkeypatch, fixture_path)
    connection = fake_pg.connect(host='localhost', password='secret')
    cursor = connection.cursor(row_factory=lambda row: row)
    cursor.execute('SHOW STATS')
    assert list(cursor) == [{'database': 'example', 'avg_recv': 1}]

    install_replay_psycopg(monkeypatch, fixture_path)
    connection = fake_pg.connect(host='localhost', password='secret')
    cursor = connection.cursor(row_factory=lambda row: row)
    cursor.execute('SHOW STATS')
    assert list(cursor) == [{'database': 'example', 'avg_recv': 1}]


def test_normalize_output_sorts_metadata():
    output = {
        'metrics': [],
        'service_checks': [],
        'events': [],
        'event_platform_events': {},
        'metadata': [
            {'check_id': 'b', 'name': 'version.raw', 'value': '2.0.0'},
            {'check_id': 'a', 'name': 'version.raw', 'value': '1.0.0'},
        ],
    }

    normalized = normalize_output(output)

    assert [item['check_id'] for item in normalized['metadata']] == ['a', 'b']


def test_serialize_aggregator_includes_base_agent_outputs(aggregator, datadog_agent, dd_run_check):
    datadog_agent._sent_telemetry.clear()
    check = AgentOutputReplayCheck('agent_output_replay', {}, [{}])
    check.check_id = 'agent_output_replay:123'

    dd_run_check(check)

    output = normalize_output(serialize_aggregator(aggregator, datadog_agent))

    assert output['metrics'][0]['name'] == 'agent_output_replay.metric'
    assert output['metadata'] == [
        {'check_id': 'agent_output_replay:123', 'name': 'flavor', 'value': {'name': 'example'}},
        {'check_id': 'agent_output_replay:123', 'name': 'version.raw', 'value': '1.2.3'},
    ]
    assert output['external_tags'] == [
        {'hostname': 'external.example', 'source_map': {'src': ['a:1', 'z:9']}},
    ]
    assert {'key': 'agent_output_replay:123_cursor', 'value': 'abc'} in output['persistent_cache']
    assert {'key': 'agent_output_replay:123_log_cursor_default', 'value': '{"offset":2}'} in output['persistent_cache']
    assert output['agent_logs'] == [
        {
            'check_id': 'agent_output_replay:123',
            'index': 0,
            'log': {'message': 'hello'},
        },
    ]
    assert output['telemetry'] == [
        {
            'check_name': 'agent_output_replay',
            'metric_name': 'telemetry.metric',
            'metric_type': 'gauge',
            'value': 7,
        },
    ]
