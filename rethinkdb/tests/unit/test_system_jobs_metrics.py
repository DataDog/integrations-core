# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.rethinkdb import queries
from datadog_checks.rethinkdb.config import Config
from datadog_checks.rethinkdb.types import BackfillJob, DiskCompactionJob, IndexConstructionJob, QueryJob

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

    mock_request_response_query_job_row = {
        'type': 'query',
        'id': ('query', 'abcd1234'),
        'duration_sec': 0.12,
        'info': {},
        'servers': ['server0'],
    }  # type: QueryJob

    mock_changefeed_query_job_row = {
        'type': 'query',
        'id': ('query', 'abcd1234'),
        'duration_sec': 10,
        'info': {},
        'servers': ['server1'],
    }  # type: QueryJob

    mock_disk_compaction_row = {
        'type': 'disk_compaction',
        'id': ('disk_compaction', 'zero'),
        'duration_sec': None,
        'info': {},
        'servers': ['server0'],
    }  # type: DiskCompactionJob

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

    mock_rows = [
        mock_request_response_query_job_row,
        mock_changefeed_query_job_row,
        mock_disk_compaction_row,
        mock_backfill_job_row,
        mock_index_construction_job_row,
    ]

    conn = mock.Mock()
    with mock.patch('rethinkdb.ast.RqlQuery.run') as run:
        run.return_value = mock_rows
        metrics = list(queries.system_jobs.run(conn=conn, config=Config({'min_collection_interval': 5})))

    assert metrics == [
        # short request-response `query` job ignored
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.duration_sec',
            'value': 10,
            'tags': ['job_type:query', 'server:server1'],
        },
        # `disk_compaction` job ignored
        {
            'type': 'gauge',
            'name': 'rethinkdb.jobs.duration_sec',
            'value': 0.42,
            'tags': [
                'job_type:backfill',
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
            'name': 'rethinkdb.jobs.duration_sec',
            'value': 0.24,
            'tags': [
                'job_type:index_construction',
                'server:server1',
                'database:doghouse',
                'table:heroes',
                'index:appearances_count',
            ],
        },
    ]


def test_unknown_job():
    # type: () -> None
    """
    If a new job type is added, an exception should be raised so we are notified via CI failures and can add support.
    """
    mock_unknown_job_row = {'type': 'an_unknown_type_that_should_be_ignored', 'duration_sec': 0.42, 'servers': []}

    conn = mock.Mock()
    with mock.patch('rethinkdb.ast.RqlQuery.run') as run:
        run.return_value = [mock_unknown_job_row]
        with pytest.raises(RuntimeError):
            list(queries.system_jobs.run(conn=conn, config=Config()))
