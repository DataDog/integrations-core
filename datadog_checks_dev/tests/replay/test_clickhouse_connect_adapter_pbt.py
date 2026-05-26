# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from datadog_checks.dev.replay.adapters.clickhouse_connect import (
    install_live_recording_clickhouse_connect,
    install_replay_clickhouse_connect,
)

safe_text = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters=['\x00']),
    max_size=120,
)
non_empty_safe_text = safe_text.filter(bool)
json_scalars = st.one_of(st.none(), st.booleans(), st.integers(min_value=-10_000, max_value=10_000), safe_text)
rows = st.lists(st.lists(json_scalars, max_size=5), max_size=8)
kwargs = st.dictionaries(st.sampled_from(['host', 'port', 'username', 'password', 'database']), json_scalars, max_size=5)

pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])


class FakeQueryResult:
    def __init__(self, result_rows: list[list[Any]]):
        self.result_rows = result_rows
        self.column_names = ['col']
        self.column_types = ['String']


class FakeClient:
    def __init__(self, *, query_rows=None, command_result='24.8.1', ping_result=True):
        self.query_rows = query_rows or []
        self.command_result = command_result
        self.ping_result = ping_result
        self.closed = False

    def query(self, query, *args, **kwargs):
        return FakeQueryResult(self.query_rows)

    def command(self, command, *args, **kwargs):
        return self.command_result

    def ping(self):
        return self.ping_result

    def close(self):
        self.closed = True


def install_fake_clickhouse_connect(monkeypatch: pytest.MonkeyPatch, client: FakeClient | None = None):
    module = types.ModuleType('clickhouse_connect')
    module.client = client or FakeClient()

    def get_client(*args, **kwargs):
        return module.client

    module.get_client = get_client
    monkeypatch.setitem(sys.modules, 'clickhouse_connect', module)
    return module


@pbt_settings
@given(connect_kwargs=kwargs, sql=non_empty_safe_text, result_rows=rows)
def test_clickhouse_connect_record_and_replay_query_rows(tmp_path, connect_kwargs, sql, result_rows):
    monkeypatch = pytest.MonkeyPatch()
    try:
        fake_clickhouse_connect = install_fake_clickhouse_connect(monkeypatch, FakeClient(query_rows=result_rows))
        fixture_path = tmp_path / 'capture.json'

        recorded = install_live_recording_clickhouse_connect(monkeypatch, fixture_path)
        client = fake_clickhouse_connect.get_client(**connect_kwargs, pool_mgr=object())
        assert client.query(sql, parameters={'limit': 1}).result_rows == result_rows

        assert recorded[0]['operation'] == 'clickhouse_connect.get_client'
        assert recorded[0]['kwargs'].get('pool_mgr') == '<POOL_MANAGER>'
        if 'password' in connect_kwargs:
            assert recorded[0]['kwargs']['password'] == '<REDACTED>'

        replayed = install_replay_clickhouse_connect(monkeypatch, fixture_path)
        replay_client = fake_clickhouse_connect.get_client(**connect_kwargs, pool_mgr=object())

        assert replay_client.query(sql, parameters={'limit': 1}).result_rows == result_rows
        assert [record['operation'] for record in replayed] == [
            'clickhouse_connect.get_client',
            'clickhouse.client.query',
        ]
    finally:
        monkeypatch.undo()


@pbt_settings
@given(connect_kwargs=kwargs, command=non_empty_safe_text, command_result=json_scalars, ping_result=st.booleans())
def test_clickhouse_connect_replay_round_trips_command_ping_and_close(
    tmp_path, connect_kwargs, command, command_result, ping_result
):
    monkeypatch = pytest.MonkeyPatch()
    try:
        fake_clickhouse_connect = install_fake_clickhouse_connect(
            monkeypatch, FakeClient(command_result=command_result, ping_result=ping_result)
        )
        fixture_path = tmp_path / 'capture.json'

        install_live_recording_clickhouse_connect(monkeypatch, fixture_path)
        client = fake_clickhouse_connect.get_client(**connect_kwargs)
        assert client.command(command, use_database=False) == command_result
        assert client.ping() is ping_result
        client.close()

        install_replay_clickhouse_connect(monkeypatch, fixture_path)
        replay_client = fake_clickhouse_connect.get_client(**connect_kwargs)

        assert replay_client.command(command, use_database=False) == command_result
        assert replay_client.ping() is ping_result
        assert replay_client.close() is None
    finally:
        monkeypatch.undo()


@pbt_settings
@given(sql_a=non_empty_safe_text, sql_b=non_empty_safe_text)
def test_clickhouse_connect_replay_rejects_wrong_query(tmp_path, sql_a, sql_b):
    assume(sql_a != sql_b)
    monkeypatch = pytest.MonkeyPatch()
    try:
        fake_clickhouse_connect = install_fake_clickhouse_connect(monkeypatch)
        fixture_path = tmp_path / 'capture.json'
        fixture_path.write_text(
            json.dumps(
                [
                    {'operation': 'clickhouse_connect.get_client', 'args': [], 'kwargs': {}, 'exception': None},
                    {
                        'operation': 'clickhouse.client.query',
                        'sql': sql_a,
                        'args': [],
                        'kwargs': {},
                        'result_rows': [],
                        'exception': None,
                    },
                ]
            )
            + '\n'
        )

        install_replay_clickhouse_connect(monkeypatch, fixture_path)
        client = fake_clickhouse_connect.get_client()
        with pytest.raises(AssertionError, match='query does not match'):
            client.query(sql_b)
    finally:
        monkeypatch.undo()


@pbt_settings
@given(sql=non_empty_safe_text)
def test_clickhouse_connect_replay_rejects_exhausted_records(tmp_path, sql):
    monkeypatch = pytest.MonkeyPatch()
    try:
        fake_clickhouse_connect = install_fake_clickhouse_connect(monkeypatch)
        fixture_path = tmp_path / 'capture.json'
        fixture_path.write_text(
            json.dumps([{'operation': 'clickhouse_connect.get_client', 'args': [], 'kwargs': {}, 'exception': None}])
            + '\n'
        )

        install_replay_clickhouse_connect(monkeypatch, fixture_path)
        client = fake_clickhouse_connect.get_client()
        with pytest.raises(AssertionError, match='No recorded ClickHouse operation'):
            client.query(sql)
    finally:
        monkeypatch.undo()


@pbt_settings
@given(message=non_empty_safe_text)
def test_clickhouse_connect_replay_round_trips_recorded_runtime_errors(tmp_path, message):
    monkeypatch = pytest.MonkeyPatch()
    try:
        fake_clickhouse_connect = install_fake_clickhouse_connect(monkeypatch)
        fixture_path = tmp_path / 'capture.json'
        fixture_path.write_text(
            json.dumps(
                [
                    {'operation': 'clickhouse_connect.get_client', 'args': [], 'kwargs': {}, 'exception': None},
                    {
                        'operation': 'clickhouse.client.ping',
                        'result': None,
                        'exception': {'type': 'RuntimeError', 'module': 'builtins', 'message': message},
                    },
                ]
            )
            + '\n'
        )

        install_replay_clickhouse_connect(monkeypatch, fixture_path)
        client = fake_clickhouse_connect.get_client()
        with pytest.raises(RuntimeError) as exc_info:
            client.ping()

        assert str(exc_info.value) == message
    finally:
        monkeypatch.undo()
