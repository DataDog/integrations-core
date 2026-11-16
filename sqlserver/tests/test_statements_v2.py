# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from concurrent.futures.thread import ThreadPoolExecutor
from copy import deepcopy

import mock
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.statements import _row_key
from datadog_checks.sqlserver.statements_v2 import (
    STATEMENT_TEXT_BATCH_SIZES,
    SqlserverStatementMetricsV2,
    padded_batches,
    split_plan_handle_and_offsets,
)
from datadog_checks.sqlserver.utils import construct_use_statement

from .common import CHECK_NAME
from .utils import CLOSE_TO_ZERO_INTERVAL

# Executions shared by the integration tests: a parameterized statement, a procedure with parameters, a multi-statement
# procedure in another database, and an encrypted procedure, whose text SQL Server does not return.
WORKLOAD = [
    ("datadog_test-1", "SELECT * FROM ϑings where id = ?", (1,)),
    ("datadog_test-1", "SELECT * FROM ϑings where id = ?", (2,)),
    ("datadog_test-1", "EXEC bobProcParams @P1 = ?, @P2 = ?", (1, "foo")),
    ("master", "EXEC multiQueryProc", ()),
    ("master", "EXEC encryptedProc", ()),
]


def _is_workload_text(text: str | None) -> bool:
    return bool(text) and ('ϑings' in text or 'select @total' in text.lower())


def _is_workload_row(row: dict) -> bool:
    return _is_workload_text(row['text']) or row['is_encrypted']


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': CLOSE_TO_ZERO_INTERVAL,
        'collect_plans': False,
        'incremental_query_metrics': True,
    }
    return deepcopy(instance_docker)


@pytest.mark.unit
@pytest.mark.parametrize(
    'plan_handle_and_offsets,expected',
    [
        pytest.param(
            # The handle is cut to 64 characters when encoded, so its last 33 bytes come back as zeros.
            '0x' + '06000500ABCDEF01' * 3 + '06000500ABCDEF' + '0x0000002A' + '0xFFFFFFFF',
            ('06000500abcdef01' * 3 + '06000500abcdef' + '00' * 33, 42, -1),
            id='statement_runs_to_end_of_batch',
        ),
        pytest.param(
            '0x' + '02' * 31 + '0x00000100' + '0x000001F4',
            ('02' * 31 + '00' * 33, 256, 500),
            id='statement_in_middle_of_batch',
        ),
    ],
)
def test_split_plan_handle_and_offsets(plan_handle_and_offsets, expected):
    assert split_plan_handle_and_offsets(plan_handle_and_offsets) == expected


@pytest.mark.unit
@pytest.mark.parametrize('count', [1, 3, 64, 65, 200])
def test_padded_batches_cover_keys_with_fixed_sizes(count):
    keys = ['key-{}'.format(i) for i in range(count)]

    batches = list(padded_batches(keys))

    assert all(len(batch) in STATEMENT_TEXT_BATCH_SIZES for batch in batches)
    assert [key for batch in batches for key in dict.fromkeys(batch)] == keys


class TextCursor:
    """Answers the statement text query from a fixed mapping of keys to text."""

    def __init__(self, texts: dict[str, str], error: Exception | None = None):
        self._texts = texts
        self._error = error
        self._rows: list[tuple] = []
        self.description = [('statement_key',), ('statement_text',), ('text',), ('is_encrypted',)]
        self.read_keys: list[str] = []

    def execute(self, query, params):
        if self._error is not None:
            raise self._error
        keys = list(dict.fromkeys(params[0::3]))
        self.read_keys.extend(keys)
        self._rows = [(key, self._texts[key], self._texts[key], False) for key in keys if key in self._texts]

    def fetchall(self):
        return self._rows


def _changed(*keys: str) -> list[dict]:
    return [{'statement_key': key, 'sproc_object_id': None} for key in keys]


@pytest.fixture
def statement_metrics(instance_docker) -> SqlserverStatementMetricsV2:
    instance_docker['dbm'] = True
    instance_docker['query_metrics'] = {'enabled': True, 'run_sync': True, 'incremental_query_metrics': True}
    return SQLServer(CHECK_NAME, {}, [instance_docker]).statement_metrics


@pytest.mark.unit
def test_resolve_reads_each_statement_once(statement_metrics, datadog_agent):
    def _obfuscate_sql(sql_query, options=None):
        if sql_query == 'SELECT broken':
            raise ValueError('cannot obfuscate')
        return json.dumps({'query': sql_query, 'metadata': {}})

    cursor = TextCursor({'a': 'SELECT a', 'b': 'SELECT broken'})
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _obfuscate_sql
        first = statement_metrics._resolve_statements(cursor, {'a', 'b'}, _changed('a', 'b'))
        second = statement_metrics._resolve_statements(cursor, {'a', 'b'}, _changed('a', 'b'))

    assert set(first) == set(second) == {'a'}
    assert second['a']['text'] == 'SELECT a'
    # The statement that failed obfuscation is not read again either, since its text cannot change.
    assert sorted(cursor.read_keys) == ['a', 'b']


@pytest.mark.unit
def test_resolve_drops_statements_that_left_the_snapshot(statement_metrics):
    cursor = TextCursor({'a': 'SELECT a', 'b': 'SELECT b'})
    statement_metrics._resolve_statements(cursor, {'a', 'b'}, _changed('a', 'b'))

    statement_metrics._resolve_statements(cursor, {'b'}, [])
    statement_metrics._resolve_statements(cursor, {'a', 'b'}, _changed('a', 'b'))

    assert cursor.read_keys == ['a', 'b', 'a']


@pytest.mark.unit
def test_resolve_reports_cached_statements_when_text_read_fails(statement_metrics):
    statement_metrics._resolve_statements(TextCursor({'a': 'SELECT a'}), {'a'}, _changed('a'))

    resolved = statement_metrics._resolve_statements(
        TextCursor({}, error=RuntimeError('connection lost')), {'a', 'b'}, _changed('a', 'b')
    )

    assert set(resolved) == {'a'}


def _run_workload(bob_conn):
    for database, query, params in WORKLOAD:
        bob_conn.execute_with_retries(query, params, database=database)


def _collect_rows(aggregator, dd_run_check, check, include=_is_workload_row) -> dict[tuple, dict]:
    aggregator.reset()
    dd_run_check(check)
    payloads = [p for p in aggregator.get_event_platform_events("dbm-metrics") if p.get('kind') == 'query_metrics']
    rows = [row for payload in payloads for row in payload['sqlserver_rows'] if include(row)]
    return {_row_key(row): row for row in rows}


def _v1_and_v2(instance: dict) -> tuple[SQLServer, SQLServer]:
    v1_instance = deepcopy(instance)
    v1_instance['query_metrics']['incremental_query_metrics'] = False
    return SQLServer(CHECK_NAME, {}, [v1_instance]), SQLServer(CHECK_NAME, {}, [instance])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('disable_secondary_tags', [False, True])
def test_incremental_rows_match_v1(aggregator, dd_run_check, dbm_instance, bob_conn, disable_secondary_tags):
    dbm_instance['query_metrics']['disable_secondary_tags'] = disable_secondary_tags
    v1, v2 = _v1_and_v2(dbm_instance)

    # Two collections establish each collector's lookback window and counter baseline for the workload.
    for _ in range(2):
        for check in (v1, v2):
            dd_run_check(check)
        _run_workload(bob_conn)

    # The first comparison resolves the workload's text from the database, the second from the cache.
    for _ in range(2):
        v1_rows = _collect_rows(aggregator, dd_run_check, v1)
        v2_rows = _collect_rows(aggregator, dd_run_check, v2)
        assert v1_rows, "v1 should have reported the workload"
        assert v2_rows == v1_rows
        _run_workload(bob_conn)


def _run_altered_procedure(cursor):
    cursor.execute("EXEC incrementalAlteredProc")
    cursor.fetchall()
    while cursor.nextset():
        cursor.fetchall()


def _is_row_of(sproc_object_id: int):
    return lambda row: row.get('sproc_object_id') == sproc_object_id


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'before,after',
    [
        pytest.param("SELECT id FROM ϑings WHERE id > 1", "SELECT id FROM ϑings WHERE id < 1", id='statement_changed'),
        pytest.param(
            "BEGIN SELECT id FROM ϑings; SELECT name FROM ϑings; END",
            "BEGIN SELECT id FROM ϑings; SELECT id, name FROM ϑings; END",
            id='other_statement_changed',
        ),
    ],
)
@pytest.mark.parametrize('disable_secondary_tags', [False, True])
def test_incremental_rows_match_v1_after_procedure_altered(
    aggregator, dd_run_check, dbm_instance, sa_conn, before, after, disable_secondary_tags
):
    # Altering a procedure keeps its plan handle, and the offsets of the statements whose length did not change.
    dbm_instance['query_metrics']['disable_secondary_tags'] = disable_secondary_tags
    v1, v2 = _v1_and_v2(dbm_instance)
    with sa_conn.cursor() as cursor:
        cursor.execute(construct_use_statement('datadog_test-1'))
        try:
            for body in (before, after):
                cursor.execute("CREATE OR ALTER PROCEDURE incrementalAlteredProc AS " + body)
                is_procedure_row = _is_row_of(cursor.execute("SELECT OBJECT_ID('incrementalAlteredProc')").fetchval())
                # Baseline, then text read from the database, then from the cache.
                for _ in range(3):
                    _run_altered_procedure(cursor)
                    v1_rows = _collect_rows(aggregator, dd_run_check, v1, is_procedure_row)
                    v2_rows = _collect_rows(aggregator, dd_run_check, v2, is_procedure_row)
                assert v1_rows, "v1 should have reported the procedure"
                assert v2_rows == v1_rows
        finally:
            cursor.execute("DROP PROCEDURE IF EXISTS incrementalAlteredProc")


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_incremental_obfuscates_repeated_statements_once(dd_run_check, dbm_instance, bob_conn, datadog_agent):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        for _ in range(3):
            dd_run_check(check)
            _run_workload(bob_conn)
        assert any(_is_workload_text(call.args[0]) for call in mock_agent.call_args_list)

        mock_agent.reset_mock()
        dd_run_check(check)

    assert not [call.args[0] for call in mock_agent.call_args_list if _is_workload_text(call.args[0])]
