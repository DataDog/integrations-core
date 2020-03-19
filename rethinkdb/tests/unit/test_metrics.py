# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Unit tests for metrics that are hard to test using integration tests, eg. because they depend on cluster dynamics.
"""
import mock
import pytest

from datadog_checks.rethinkdb.metrics.system_jobs import collect_system_jobs
from datadog_checks.rethinkdb.types import BackfillJob, IndexConstructionJob

pytestmark = pytest.mark.unit


def test_jobs_metrics():
    # type: () -> None
    """
    Verify jobs metrics submitted by RethinkDB are processed correctly.

    We provide unit tests for these metrics because testing them in a live environment is tricky.

    For example:
    * Backfill jobs can only be seen by us when large amounts of data is rebalanced between servers, e.g.
    when a new server is added to the cluster, or an existing server is shut down.
    * Index construction jobs can only be seen by us when a secondary index is added to a relatively large table.
    * Query jobs can only be seen by us when an external client issues queries to the cluster.
    * Etc.
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
        'duration_sec': 0.24,
        'info': {'db': 'doghouse', 'table': 'heroes', 'index': 'appearances_count', 'progress': 42},
        'servers': ['server1'],
    }  # type: IndexConstructionJob

    mock_unknown_job_row = {'type': 'an_unknown_type_that_should_be_ignored', 'duration_sec': 0.42, 'servers': []}

    mock_rows = [mock_backfill_job_row, mock_index_construction_job_row, mock_unknown_job_row]

    conn = mock.Mock()
    with mock.patch('rethinkdb.ast.RqlQuery.run') as run:
        run.return_value = mock_rows
        metrics = list(collect_system_jobs(conn))

    assert metrics == [
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.duration',
            'value': 0.42,
            'tags': [
                'server:server0',
                'server:server2',
                'job_type:backfill',
                'database:doghouse',
                'destination_server:server2',
                'source_server:server0',
                'table:heroes',
            ],
        },
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.duration',
            'value': 0.24,
            'tags': [
                'server:server1',
                'job_type:index_construction',
                'database:doghouse',
                'table:heroes',
                'index:appearances_count',
            ],
        },
    ]
