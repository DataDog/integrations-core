# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.stubs import aggregator as _aggregator_stub
from datadog_checks.cloud_spanner import SpannerCheck


@pytest.fixture
def aggregator():
    _aggregator_stub.reset()
    yield _aggregator_stub
    _aggregator_stub.reset()


@pytest.fixture
def dd_run_check():
    def run(check):
        error = check.run()
        if error:
            raise Exception(error)

    return run


INSTANCE_CONFIG = {
    'project_id': 'test-project',
    'instance_id': 'test-instance',
    'database': 'test-database',
    'dbm': True,
    'query_metrics': {
        'enabled': True,
        'collection_interval': 0.1,
    },
    'tags': ['env:test', 'service:myapp'],
}

INTERVAL_END = datetime(2025, 6, 24, 12, 1, 0, tzinfo=timezone.utc)

# Rows returned by SPANNER_SYS.QUERY_STATS_TOP_MINUTE.
# Column order must match QUERY_STATS_COLUMNS in queries.py:
#   interval_end, request_tag, query_type, text, text_truncated, text_fingerprint,
#   execution_count, avg_latency_seconds, avg_rows, avg_bytes, avg_rows_scanned,
#   avg_cpu_seconds, all_failed_execution_count, all_failed_avg_latency_seconds,
#   cancelled_or_disconnected_execution_count, timed_out_execution_count
MOCK_QUERY_STATS_ROWS = [
    (
        INTERVAL_END,
        'api/list-users',
        'GLOBAL',
        'SELECT user_id, name FROM users WHERE status = @status',
        False,
        1234567890,
        150,
        0.023,
        10.5,
        2048.0,
        1000.0,
        0.015,
        2,
        0.5,
        0,
        0,
    ),
    (
        INTERVAL_END,
        '',
        'PARTITIONED_QUERY',
        'SELECT * FROM orders',
        False,
        9876543210,
        5,
        1.2,
        50000.0,
        1024000.0,
        50000.0,
        0.8,
        0,
        0.0,
        1,
        0,
    ),
    (
        INTERVAL_END,
        'batch/nightly-report',
        'GLOBAL',
        'SELECT COUNT(*) FROM events WHERE created_at > @cutoff',
        False,
        1122334455,
        3,
        0.05,
        1.0,
        8.0,
        100.0,
        0.002,
        0,
        0.0,
        0,
        1,
    ),
]


def _build_mock_spanner_client(rows=None):
    if rows is None:
        rows = MOCK_QUERY_STATS_ROWS

    mock_snapshot = MagicMock()
    mock_snapshot.execute_sql.return_value = rows

    snapshot_ctx = MagicMock()
    snapshot_ctx.__enter__ = MagicMock(return_value=mock_snapshot)
    snapshot_ctx.__exit__ = MagicMock(return_value=False)

    mock_database = MagicMock()
    mock_database.snapshot.return_value = snapshot_ctx

    mock_instance = MagicMock()
    mock_instance.database.return_value = mock_database

    mock_client = MagicMock()
    mock_client.instance.return_value = mock_instance

    return mock_client, mock_snapshot


@pytest.fixture
def mock_spanner_client():
    client, snapshot = _build_mock_spanner_client()
    return client, snapshot


@pytest.fixture
def check(mock_spanner_client):
    mock_client, _ = mock_spanner_client
    instance = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
    instance._client = mock_client  # inject mock — bypasses _create_spanner_client
    return instance
