# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import ibm_db
import pytest

from datadog_checks.dev import WaitFor
from datadog_checks.ibm_db2.activity import ACTIVITY_MAX_TEXT_BYTES, read_activity
from datadog_checks.ibm_db2.connection import get_connection_data

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def _execute(connection: Any, query: str) -> None:
    cursor = ibm_db.exec_immediate(connection, query)
    ibm_db.free_stmt(cursor)


def test_activity_reader(instance: dict):
    """Read concurrent executions, omit Agent/oversized SQL, and stop reporting work after it completes."""
    target, user, password = get_connection_data(
        instance['db'], instance['username'], instance['password'], instance['host'], instance['port'], None, None, None
    )

    def connect() -> Any:
        return ibm_db.connect(target, user, password, {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER})

    table = f'DB2INST1.DBM_ACTIVITY_{uuid4().hex.upper()}'
    admin, observer = connect(), connect()
    created = False
    try:
        _execute(admin, f'CREATE TABLE {table} (ID INTEGER NOT NULL PRIMARY KEY, VALUE VARCHAR(100))')
        created = True
        _execute(admin, f"INSERT INTO {table} VALUES (1, 'seed')")
        ibm_db.autocommit(admin, ibm_db.SQL_AUTOCOMMIT_OFF)
        _execute(admin, f"UPDATE {table} SET VALUE='held' WHERE ID=1")

        def blocked_update(query: str) -> None:
            connection = connect()
            try:
                _execute(connection, query)
            finally:
                ibm_db.close(connection)

        queries = [f"UPDATE {table} SET VALUE='literal-{n}' WHERE ID=1" for n in range(4)]
        queries[2] = "/* service='datadog-agent' */ " + queries[2]
        queries[3] += ' /*' + 'é' * ACTIVITY_MAX_TEXT_BYTES + '*/'
        with ThreadPoolExecutor(max_workers=4) as workers:
            futures = [workers.submit(blocked_update, query) for query in queries]
            try:

                def assert_active() -> None:
                    rows, stats = read_activity(observer)
                    matching = [row for row in rows if table in (row['stmt_text'] or '')]
                    assert {row['stmt_text'] for row in matching} == set(queries[:2])
                    assert len({row['application_handle'] for row in matching}) == 2
                    assert all(row['observed_timestamp'] > row['local_start_time'] for row in matching)
                    assert all(row['session_auth_id'].strip() == instance['username'].upper() for row in matching)
                    assert stats == {'row_limit': 0, 'text_limit': 1, 'text_budget': 0}

                WaitFor(assert_active, attempts=40, wait=0.25)()
            finally:
                ibm_db.rollback(admin)
            for future in futures:
                future.result(timeout=30)
        rows, _ = read_activity(observer)
        assert not any(table in (row['stmt_text'] or '') for row in rows)
    finally:
        ibm_db.rollback(admin)
        ibm_db.autocommit(admin, ibm_db.SQL_AUTOCOMMIT_ON)
        if created:
            _execute(admin, f'DROP TABLE {table}')
        ibm_db.close(admin)
        ibm_db.close(observer)
