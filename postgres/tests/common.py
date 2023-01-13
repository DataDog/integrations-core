# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from sys import maxsize

import pytest

from datadog_checks.dev import get_docker_hostname
from datadog_checks.postgres.util import SLRU_METRICS

HOST = get_docker_hostname()
PORT = '5432'
USER = 'datadog'
PASSWORD = 'datadog'
DB_NAME = 'datadog_test'
POSTGRES_VERSION = os.environ.get('POSTGRES_VERSION', None)
POSTGRES_IMAGE = "alpine"

USING_LATEST = False

if POSTGRES_VERSION is not None:
    USING_LATEST = POSTGRES_VERSION.endswith('latest')
    POSTGRES_IMAGE = POSTGRES_VERSION + "-alpine"

if USING_LATEST is True:
    POSTGRES_VERSION = str(maxsize)
    POSTGRES_IMAGE = "alpine"

SCHEMA_NAME = 'schemaname'

COMMON_METRICS = [
    'postgresql.before_xid_wraparound',
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
    'postgresql.deadlocks.count',
    'postgresql.temp_bytes',
    'postgresql.temp_files',
]

DBM_MIGRATED_METRICS = [
    'postgresql.connections',
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
CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']
CONNECTION_METRICS_DB = ['postgresql.connections']
COMMON_DBS = ['dogs', 'postgres', 'dogs_nofunc', 'dogs_noschema', DB_NAME]

requires_static_version = pytest.mark.skipif(USING_LATEST, reason='Version `latest` is ever-changing, skipping')


def check_common_metrics(aggregator, expected_tags, count=1):
    for db in COMMON_DBS:
        db_tags = expected_tags + ['db:{}'.format(db)]
        for name in COMMON_METRICS:
            aggregator.assert_metric(name, count=count, tags=db_tags)


def check_db_count(aggregator, expected_tags, count=1):
    aggregator.assert_metric(
        'postgresql.table.count', value=5, count=count, tags=expected_tags + ['db:{}'.format(DB_NAME), 'schema:public']
    )
    aggregator.assert_metric('postgresql.db.count', value=5, count=1)


def check_connection_metrics(aggregator, expected_tags, count=1):
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=count, tags=expected_tags)
    for db in COMMON_DBS:
        db_tags = expected_tags + ['db:{}'.format(db)]
        for name in CONNECTION_METRICS_DB:
            aggregator.assert_metric(name, count=count, tags=db_tags)


def check_activity_metrics(aggregator, tags, hostname=None, count=1):
    activity_metrics = [
        'postgresql.transactions.open',
        'postgresql.transactions.idle_in_transaction',
        'postgresql.active_queries',
        'postgresql.waiting_queries',
        'postgresql.active_waiting_queries',
        'postgresql.activity.xact_start_age',
    ]
    if POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 9.6:
        # Query won't have xid assigned so postgresql.activity.backend_xid_age won't be emitted
        activity_metrics.append('postgresql.activity.backend_xmin_age')
    for name in activity_metrics:
        aggregator.assert_metric(name, count=1, tags=tags, hostname=hostname)


def is_tag_in_excluded(tag, excluded_tags):
    for excluded_tag in excluded_tags:
        if tag.startswith(excluded_tag):
            return True
    return False


def set_tag_to_value(tag, tags_to_replace, replace_value):
    for tag_to_replace in tags_to_replace:
        if tag.startswith(tag_to_replace):
            if replace_value is None:
                return None
            else:
                return '{}:{}'.format(tag_to_replace, replace_value)
    return tag


def check_wait_event_metrics(aggregator, tags, hostname=None, count=1):
    if float(POSTGRES_VERSION) < 10.0:
        return

    launch_wait_event_tuple = [
        'backend_type:logical replication launcher',
        'wait_event:LogicalLauncherMain',
        'wait_event_type:Activity',
    ]
    if float(POSTGRES_VERSION) < 11.0:
        launch_wait_event_tuple = [
            'backend_type:background worker',
            'wait_event:LogicalLauncherMain',
            'wait_event_type:Activity',
        ]
    system_wait_event_tuples = [
        ['backend_type:walwriter', 'wait_event:WalWriterMain', 'wait_event_type:Activity'],
        ['backend_type:background writer', 'wait_event:BgWriterMain', 'wait_event_type:Activity'],
        ['backend_type:checkpointer', 'wait_event:CheckpointerMain', 'wait_event_type:Activity'],
        ['backend_type:autovacuum launcher', 'wait_event:AutoVacuumMain', 'wait_event_type:Activity'],
    ]
    # No db, user nor app for system processes
    system_tags = [set_tag_to_value(t, ['db', 'user', 'app'], None) for t in tags]
    system_tags = [t for t in system_tags if t]

    launch_tags = [set_tag_to_value(t, ['user'], 'postgres') for t in tags]
    launch_tags = [set_tag_to_value(t, ['db', 'app'], None) for t in launch_tags]
    launch_tags = [t for t in launch_tags if t]

    for wait_event_tag in system_wait_event_tuples:
        aggregator.assert_metric(
            'postgresql.activity.wait_event_count', count=1, tags=system_tags + wait_event_tag, hostname=hostname
        )

    aggregator.assert_metric(
        'postgresql.activity.wait_event_count', count=1, tags=launch_tags + launch_wait_event_tuple, hostname=hostname
    )


def check_bgw_metrics(aggregator, expected_tags, count=1):
    for name in COMMON_BGW_METRICS:
        aggregator.assert_metric(name, count=count, tags=expected_tags)

    if float(POSTGRES_VERSION) >= 9.4:
        for name in COMMON_BGW_METRICS_PG_ABOVE_94:
            aggregator.assert_metric(name, count=count, tags=expected_tags)


def check_slru_metrics(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 13.0:
        return

    slru_caches = ['Subtrans', 'Serial', 'MultiXactMember', 'Xact', 'other', 'Notify', 'CommitTs', 'MultiXactOffset']
    for (metric_name, _) in SLRU_METRICS['metrics'].values():
        for slru_cache in slru_caches:
            aggregator.assert_metric(metric_name, count=count, tags=expected_tags + ['slru_name:{}'.format(slru_cache)])
