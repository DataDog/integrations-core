# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from binascii import hexlify
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import ibm_db
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.dev import WaitFor
from datadog_checks.ibm_db2.activity import ACTIVITY_MAX_TEXT_BYTES, read_activity
from datadog_checks.ibm_db2.connection import get_connection_data

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def _execute(connection: Any, query: str) -> None:
    cursor = ibm_db.exec_immediate(connection, query)
    ibm_db.free_stmt(cursor)


@pytest.fixture
def locked_table(instance: dict) -> Iterator[tuple[str, Any, Callable[[], Any]]]:
    target, user, password = get_connection_data(
        instance['db'], instance['username'], instance['password'], instance['host'], instance['port'], None, None, None
    )

    def connect() -> Any:
        return ibm_db.connect(target, user, password, {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER})

    table = f'DB2INST1.DBM_ACTIVITY_{uuid4().hex.upper()}'
    admin = connect()
    created = False
    try:
        _execute(admin, f'CREATE TABLE {table} (ID INTEGER NOT NULL PRIMARY KEY, VALUE VARCHAR(100))')
        created = True
        _execute(admin, f"INSERT INTO {table} VALUES (1, 'seed')")
        ibm_db.autocommit(admin, ibm_db.SQL_AUTOCOMMIT_OFF)
        _execute(admin, f"UPDATE {table} SET VALUE='held' WHERE ID=1")

        yield table, admin, connect
    finally:
        ibm_db.rollback(admin)
        ibm_db.autocommit(admin, ibm_db.SQL_AUTOCOMMIT_ON)
        if created:
            _execute(admin, f'DROP TABLE {table}')
        ibm_db.close(admin)


def _blocked_update(connect: Callable[[], Any], query: str) -> None:
    connection = connect()
    try:
        _execute(connection, query)
    finally:
        ibm_db.close(connection)


def test_activity_reader(instance: dict, locked_table: tuple[str, Any, Callable[[], Any]]):
    """Read concurrent and Agent-tagged executions, truncate UTF-8 SQL, and remove completed work."""
    table, admin, connect = locked_table
    observer = connect()
    try:
        queries = [f"UPDATE {table} SET VALUE='literal-{n}' WHERE ID=1" for n in range(5)]
        queries[2] = "/* service='datadog-agent' */ " + queries[2]
        queries[3] = '/* DDIGNORE */ ' + queries[3]
        queries[4] += ' /*' + 'é中' * ACTIVITY_MAX_TEXT_BYTES + '*/'
        with ThreadPoolExecutor(max_workers=5) as workers:
            futures = [workers.submit(_blocked_update, connect, query) for query in queries]
            try:

                def assert_active() -> None:
                    rows, stats = read_activity(observer)
                    matching = [row for row in rows if table in (row['stmt_text'] or '')]
                    short = [row for row in matching if row['stmt_text_bytes'] <= ACTIVITY_MAX_TEXT_BYTES]
                    assert {row['stmt_text'] for row in short} == set(queries[:4])
                    assert len({row['application_handle'] for row in matching}) == 5
                    long = [row for row in matching if row['stmt_text_bytes'] > ACTIVITY_MAX_TEXT_BYTES]
                    assert len(long) == 1
                    text = long[0]['stmt_text']
                    assert len(text.encode('utf-8')) <= ACTIVITY_MAX_TEXT_BYTES
                    assert text.rstrip() == queries[4].encode('utf-8')[:ACTIVITY_MAX_TEXT_BYTES].decode(
                        'utf-8', errors='ignore'
                    )
                    assert long[0]['stmt_text_bytes'] == len(queries[4].encode('utf-8'))
                    assert all(row['executable_id'] for row in matching)
                    assert all(row['observed_timestamp'] > row['local_start_time'] for row in matching)
                    assert all(row['session_auth_id'].strip() == instance['username'].upper() for row in matching)
                    assert stats == {'row_limit': 0}

                WaitFor(assert_active, attempts=40, wait=0.25)()
            finally:
                ibm_db.rollback(admin)
            for future in futures:
                future.result(timeout=30)
        rows, _ = read_activity(observer)
        assert not any(table in (row['stmt_text'] or '') for row in rows)
    finally:
        ibm_db.close(observer)


@pytest.mark.e2e
def test_query_activity_e2e(
    dd_agent_check: Callable[..., AggregatorStub],
    instance: dict,
    locked_table: tuple[str, Any, Callable[[], Any]],
):
    """The packaged Agent samples a locked query with real obfuscation, comments, timing, and executable identity."""
    table, admin, connect = locked_table
    query = f"/* ACTIVITY_E2E */ UPDATE {table} SET VALUE='literal' WHERE ID=1"
    observer = connect()
    expected = {}
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(_blocked_update, connect, query)
            try:

                def assert_active() -> None:
                    rows, _ = read_activity(observer)
                    matching = [row for row in rows if row['stmt_text'] == query]
                    assert len(matching) == 1
                    expected.update(matching[0])

                WaitFor(assert_active, attempts=40, wait=0.25)()
                instance.update(dbm=True, query_activity={'enabled': True}, query_metrics={'enabled': False})
                aggregator = dd_agent_check(instance, env_vars={'DBM_THREADED_JOB_RUN_SYNC': 'true'})
                events = aggregator.get_event_platform_events('dbm-activity')
                assert len(events) == 1
                signature = compute_sql_signature(f'UPDATE {table} SET VALUE = ? WHERE ID = ?')
                matching = [row for row in events[0]['ibm_db2_activity'] if row['query_signature'] == signature]
                assert len(matching) == 1
                row = matching[0]
                assert row['elapsed_ns'] > 0
                assert row['executable_id'] == hexlify(expected['executable_id']).decode('ascii')
                assert row['dd_comments'] == ['/* ACTIVITY_E2E */']
                assert row['query_truncated'] == 'not_truncated'
            finally:
                ibm_db.rollback(admin)
            future.result(timeout=30)
    finally:
        ibm_db.close(observer)
