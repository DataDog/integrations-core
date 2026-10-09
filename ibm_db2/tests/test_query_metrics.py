# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
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
    query = f'SELECT COUNT(*) AS DBM_QUERY_METRICS_{uuid4().hex.upper()} FROM SYSCAT.TABLES'

    def execute_query() -> None:
        cursor = ibm_db.exec_immediate(connection.conn, query)
        try:
            while ibm_db.fetch_tuple(cursor) is not False:
                pass
        finally:
            ibm_db.free_stmt(cursor)

    try:
        execute_query()
        dd_run_check(check)
        assert not aggregator.get_event_platform_events('dbm-metrics')

        # A collection with no new executions must preserve the baseline.
        dd_run_check(check)

        # Close the driver handle so the collector must recover on its next run.
        ibm_db.close(check._query_metrics._connection.conn)

        for _ in range(3):
            execute_query()

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
            assert row['query_signature'] == compute_sql_signature(query)
            assert payload['host'] == check.reported_hostname
            assert payload['timestamp'] > 0
            assert payload['ddagentversion'] == check.agent_version
            assert payload['min_collection_interval'] == collection_interval
            assert payload['ibm_db2_version'].startswith('12.01.')
            assert f"db:{instance['db']}" in payload['tags']

        WaitFor(assert_query_metric, attempts=20, wait=1)()
    finally:
        connection.close()
