# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Unit tests for metrics that are hard to test using integration tests, eg. because they depend on cluster dynamics.
"""
import pytest

from datadog_checks.rethinkdb.metrics.system_jobs import collect_system_jobs
from datadog_checks.rethinkdb.queries import QueryEngine
from datadog_checks.rethinkdb.types import BackfillJob, IndexConstructionJob

from ..utils import MockConnection

pytestmark = pytest.mark.unit


def test_jobs_metrics():
    # type: () -> None
    """
    Verify jobs metrics submitted by RethinkDB are processed correctly.

    We provide unit tests for these metrics because testing them in a live environment is tricky.
    """

    mock_backfill_job_row = {
        # See: https://rethinkdb.com/docs/system-jobs/#backfill
        'type': 'backfill',
        'id': ('backfill', 'abcd1234'),
        'duration_sec': 0.42,
        'info': {
            'db': 'doghouse',
            'table': 'heroes',
            'destination_server': 'server2',
            'source_server': 'server0',
            'progress': 42,
        },
        'servers': ['server0', 'server2'],
    }  # type: BackfillJob

    mock_index_construction_job_row = {
        # See: https://rethinkdb.com/docs/system-jobs/#index_construction
        'type': 'index_construction',
        'id': ('index_construction', 'abcd1234'),
        'duration_sec': 0.42,
        'info': {'db': 'doghouse', 'table': 'heroes', 'index': 'appearances_count', 'progress': 42},
        'servers': ['server1'],
    }  # type: IndexConstructionJob

    mock_unknown_job_row = {'type': 'an_unknown_type_that_should_be_ignored', 'duration_sec': 0.42, 'servers': []}

    mock_rows = [mock_backfill_job_row, mock_index_construction_job_row, mock_unknown_job_row]

    engine = QueryEngine()
    with MockConnection(rows=lambda: mock_rows) as conn:
        metrics = list(collect_system_jobs(engine, conn))

    assert metrics == [
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.backfill.duration',
            'value': 0.42,
            'tags': [
                'server:server0',
                'server:server2',
                'database:doghouse',
                'destination_server:server2',
                'source_server:server0',
                'table:heroes',
            ],
        },
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.backfill.progress',
            'value': 42,
            'tags': [
                'server:server0',
                'server:server2',
                'database:doghouse',
                'destination_server:server2',
                'source_server:server0',
                'table:heroes',
            ],
        },
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.index_construction.duration',
            'value': 0.42,
            'tags': ['server:server1', 'database:doghouse', 'table:heroes', 'index:appearances_count'],
        },
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.index_construction.progress',
            'value': 42,
            'tags': ['server:server1', 'database:doghouse', 'table:heroes', 'index:appearances_count'],
        },
    ]
