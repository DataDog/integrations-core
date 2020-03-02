# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
PORT = '5432'
USER = 'datadog'
PASSWORD = 'datadog'
DB_NAME = 'datadog_test'
POSTGRES_VERSION = os.environ.get('POSTGRES_VERSION', None)
SCHEMA_NAME = 'schemaname'

COMMON_METRICS = [
    'postgresql.before_xid_wraparound',
    'postgresql.connections',
    'postgresql.commits',
    'postgresql.rollbacks',
    'postgresql.disk_read',
    'postgresql.buffer_hit',
    'postgresql.rows_returned',
    'postgresql.rows_fetched',
    'postgresql.rows_inserted',
    'postgresql.rows_updated',
    'postgresql.rows_deleted',
    'postgresql.database_size',
    'postgresql.deadlocks',
    'postgresql.temp_bytes',
    'postgresql.temp_files',
]

COMMON_BGW_METRICS = [
    'postgresql.bgwriter.checkpoints_timed',
    'postgresql.bgwriter.checkpoints_requested',
    'postgresql.bgwriter.buffers_checkpoint',
    'postgresql.bgwriter.buffers_clean',
    'postgresql.bgwriter.maxwritten_clean',
    'postgresql.bgwriter.buffers_backend',
    'postgresql.bgwriter.buffers_alloc',
    'postgresql.bgwriter.buffers_backend_fsync',
    'postgresql.bgwriter.write_time',
    'postgresql.bgwriter.sync_time',
]

COMMON_BGW_METRICS_PG_ABOVE_94 = ['postgresql.archiver.archived_count', 'postgresql.archiver.failed_count']


def check_common_metrics(aggregator, expected_tags, count=1):
    for name in COMMON_METRICS:
        aggregator.assert_metric(name, count=count, tags=expected_tags)


def check_bgw_metrics(aggregator, expected_tags):
    for name in COMMON_BGW_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)

    if float(POSTGRES_VERSION) >= 9.4:
        for name in COMMON_BGW_METRICS_PG_ABOVE_94:
            aggregator.assert_metric(name, count=1, tags=expected_tags)
