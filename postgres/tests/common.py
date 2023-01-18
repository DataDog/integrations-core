# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from sys import maxsize

import pytest

from datadog_checks.base.stubs.aggregator import normalize_tags
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.docker import get_container_ip
from datadog_checks.postgres.util import (
    QUERY_PG_REPLICATION_SLOTS,
    QUERY_PG_STAT_WAL_RECEIVER,
    REPLICATION_STATS_METRICS,
    SLRU_METRICS,
)
from datadog_checks.postgres.version_utils import VersionUtils
from datadog_checks.postgres.util import NEWER_14_METRICS, SLRU_METRICS

HOST = get_docker_hostname()
PORT = '5432'
PORT_REPLICA = '5433'
USER = 'datadog'
PASSWORD = 'datadog'
DB_NAME = 'datadog_test'
POSTGRES_VERSION = os.environ.get('POSTGRES_VERSION', None)
POSTGRES_IMAGE = "alpine"

REPLICA_CONTAINER_NAME = 'compose-postgres_replica-1'
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


def assert_metric_at_least(aggregator, metric_name, lower_bound=None, higher_bound=None, count=None, tags=None):
    found_values = 0
    expected_tags = normalize_tags(tags, sort=True)
    aggregator.assert_metric(metric_name, count=count, tags=expected_tags)
    for metric in aggregator.metrics(metric_name):
        if expected_tags and expected_tags == sorted(metric.tags):
            if lower_bound is not None:
                assert metric.value >= lower_bound, 'Expected {} with tags {} to have a value >= {}, got {}'.format(
                    metric_name, expected_tags, lower_bound, metric.value
                )
            if higher_bound is not None:
                assert metric.value <= higher_bound, 'Expected {} with tags {} to have a value <= {}, got {}'.format(
                    metric_name, expected_tags, higher_bound, metric.value
                )
            found_values += 1
    if count:
        assert found_values == count, 'Expected to have {} with tags {} values for metric {}, got {}'.format(
            count, expected_tags, metric_name, found_values
        )


def check_common_metrics(aggregator, expected_tags, count=1):
    for db in COMMON_DBS:
        db_tags = expected_tags + ['db:{}'.format(db)]
        for name in COMMON_METRICS:
            aggregator.assert_metric(name, count=count, tags=db_tags)
        if POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 14.0:
            for metrics in NEWER_14_METRICS.values():
                metric_name = metrics[0]
                aggregator.assert_metric(metric_name, count=count, tags=db_tags)


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


def check_stat_replication(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 10:
        return
    replication_tags = expected_tags + [
        'wal_app_name:walreceiver',
        'wal_client_addr:{}'.format(get_container_ip(REPLICA_CONTAINER_NAME)),
        'wal_state:streaming',
        'wal_sync_state:async',
    ]
    for (metric_name, _) in REPLICATION_STATS_METRICS['metrics'].values():
        aggregator.assert_metric(metric_name, count=count, tags=replication_tags)


def check_wal_receiver_metrics(aggregator, expected_tags, count=1, connected=1):
    if float(POSTGRES_VERSION) < 10.0:
        return
    if not connected:
        aggregator.assert_metric(
            'postgresql.wal_receiver.connected', count=count, value=1, tags=expected_tags + ['status:disconnected']
        )
        return
    for column in QUERY_PG_STAT_WAL_RECEIVER['columns']:
        if column['type'] == 'tag':
            continue
        aggregator.assert_metric(column['name'], count=count, tags=expected_tags)


def check_replication_slots(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 10.0:
        return
    for column in QUERY_PG_REPLICATION_SLOTS['columns']:
        if column['type'] == 'tag':
            continue
        if 'slot_type:physical' in expected_tags and column['name'] in [
            'postgresql.replication_slot.confirmed_flush_delay_bytes',
        ]:
            continue
        if 'slot_type:logical' in expected_tags and column['name'] in [
            'postgresql.replication_slot.restart_delay_bytes',
            'postgresql.replication_slot.xmin_age',
        ]:
            continue
        aggregator.assert_metric(column['name'], count=count, tags=expected_tags)


def check_replication_delay(aggregator, metrics_cache, expected_tags, count=1):
    replication_metrics = metrics_cache.get_replication_metrics(VersionUtils.parse_version(POSTGRES_VERSION), False)
    for (metric_name, _) in replication_metrics.values():
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


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
