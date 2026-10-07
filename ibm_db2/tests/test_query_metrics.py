# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from binascii import hexlify
from collections.abc import Callable
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import ibm_db
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.dev import WaitFor
from datadog_checks.ibm_db2 import IbmDb2Check, query_metrics
from datadog_checks.ibm_db2.connection import Db2Connection

from .common import DB2_VERSION

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(not (DB2_VERSION or '').startswith('12.1.'), reason='Query metrics are tested on Db2 12.1'),
]


def test_query_metrics(
    aggregator: AggregatorStub,
    instance: dict,
    dd_run_check: Callable[[IbmDb2Check], str],
    monkeypatch: pytest.MonkeyPatch,
):
    """Collection resumes after a closed connection and reports the correct interval count and metadata."""
    monkeypatch.setenv('DBM_THREADED_JOB_RUN_SYNC', 'true')
    collection_interval = 0.0000001
    monkeypatch.setattr(query_metrics, 'COLLECTION_INTERVAL', collection_interval)
    instance['dbm'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    connection = Db2Connection(check, check._config)
    connection.connect()
    table = f'DBM_QUERY_METRICS_{uuid4().hex.upper()}'
    query = f'SELECT ID FROM {table} WHERE ID > 1'

    def execute_query() -> None:
        cursor = ibm_db.exec_immediate(connection.conn, query)
        try:
            while ibm_db.fetch_tuple(cursor) is not False:
                pass
        finally:
            ibm_db.free_stmt(cursor)

    def read_cpu_counter() -> dict:
        cursor = ibm_db.prepare(
            connection.conn,
            """/* DDIGNORE */
            SELECT MEMBER, EXECUTABLE_ID, INSERT_TIMESTAMP, TOTAL_CPU_TIME
            FROM TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))
            WHERE VARCHAR(STMT_TEXT, 1000) = ?
            """,
        )
        try:
            ibm_db.execute(cursor, (query,))
            row = ibm_db.fetch_assoc(cursor)
            assert row is not False
            assert ibm_db.fetch_assoc(cursor) is False
            return row
        finally:
            ibm_db.free_stmt(cursor)

    ibm_db.exec_immediate(connection.conn, f'CREATE TABLE {table} (ID INTEGER)')
    try:
        ibm_db.exec_immediate(connection.conn, f'INSERT INTO {table} VALUES (1), (2), (3)')
        execute_query()
        before = read_cpu_counter()
        dd_run_check(check)
        assert not aggregator.get_event_platform_events('dbm-metrics')
        instance_metadata = next(
            event
            for event in aggregator.get_event_platform_events('dbm-metadata')
            if event['kind'] == 'database_instance'
        )
        assert instance_metadata['database_instance'] == check.reported_hostname

        # A collection with no new executions must preserve the baseline.
        dd_run_check(check)

        # Close the driver handle so the collector must recover on its next run.
        ibm_db.close(check._query_metrics._connection.conn)

        for _ in range(3):
            execute_query()

        after = read_cpu_counter()
        for key in ('member', 'executable_id', 'insert_timestamp'):
            assert before[key] == after[key]
        cpu_microseconds = after['total_cpu_time'] - before['total_cpu_time']
        assert cpu_microseconds > 0

        def assert_query_metric() -> None:
            dd_run_check(check)
            payloads = aggregator.get_event_platform_events('dbm-metrics')
            matching = [
                (payload, row) for payload in payloads for row in payload['ibm_db2_rows'] if row['query'] == query
            ]
            assert len(matching) == 1
            payload, row = matching[0]
            assert row['count'] == 3
            assert row['time'] >= 0
            assert row['cpu_time'] == cpu_microseconds * 1_000
            assert row['rows_read'] == 9
            assert row['rows_returned'] == 6
            assert row['query_signature'] == compute_sql_signature(query)
            assert payload['host'] == check.reported_hostname
            assert payload['database_instance'] == instance_metadata['database_instance']
            assert payload['timestamp'] > 0
            assert payload['ddagentversion'] == check.agent_version
            assert payload['min_collection_interval'] == collection_interval
            assert payload['ibm_db2_version'].startswith('12.01.')
            assert f"db:{instance['db']}" in payload['tags']

        WaitFor(assert_query_metric, attempts=20, wait=1)()

        # Once resolved, subsequent executions keep their deltas without fetching the text again.
        with patch.object(
            check._query_metrics, '_fetch_query_texts', wraps=check._query_metrics._fetch_query_texts
        ) as fetch:
            dd_run_check(check)
            execute_query()
            dd_run_check(check)
            matching = [
                row
                for payload in aggregator.get_event_platform_events('dbm-metrics')
                for row in payload['ibm_db2_rows']
                if row['query'] == query
            ]
            assert sum(row['count'] for row in matching) == 4
            assert sum(row['rows_returned'] for row in matching) == 8
            key = (before['member'], hexlify(before['executable_id']).decode('ascii'), before['insert_timestamp'])
            assert all(key not in call.args[0] for call in fetch.call_args_list)
    finally:
        try:
            ibm_db.exec_immediate(connection.conn, f'DROP TABLE {table}')
        finally:
            connection.close()


def test_query_text_lookup_matches_lifetime(instance: dict, monkeypatch: pytest.MonkeyPatch):
    """Counter-scan keys resolve to the matching text, but not a different cache lifetime."""
    monkeypatch.setattr(query_metrics, 'TEXT_FETCH_BATCH_SIZE', 2)
    instance['dbm'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    collector = check._query_metrics
    conn = collector._connection.ensure_connected()
    expected = {}
    try:
        for _ in range(3):
            query = f'SELECT COUNT(*) AS DBM_TEXT_{uuid4().hex.upper()} FROM SYSCAT.TABLES'
            cursor = ibm_db.exec_immediate(conn, query)
            while ibm_db.fetch_tuple(cursor) is not False:
                pass
            ibm_db.free_stmt(cursor)
            cursor = ibm_db.prepare(
                conn,
                query_metrics.QUERY_METRICS + '\nWHERE VARCHAR(STMT_TEXT, 1000) = ?',
            )
            try:
                ibm_db.execute(cursor, (query,))
                row = ibm_db.fetch_assoc(cursor)
                assert row is not False
                row['executable_id'] = hexlify(row['executable_id']).decode('ascii')
                expected[query_metrics.statement_key(row)] = query
            finally:
                ibm_db.free_stmt(cursor)
        member, executable_id, inserted = next(iter(expected))
        stale_key = (member, executable_id, inserted - timedelta(seconds=1))
        assert collector._fetch_query_texts(set(expected) | {stale_key}) == expected
    finally:
        collector.shutdown()
