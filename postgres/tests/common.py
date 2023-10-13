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
    NEWER_14_METRICS,
    QUERY_PG_CONTROL_CHECKPOINT,
    QUERY_PG_REPLICATION_SLOTS,
    QUERY_PG_STAT_WAL_RECEIVER,
    QUERY_PG_UPTIME,
    REPLICATION_STATS_METRICS,
    SLRU_METRICS,
    SNAPSHOT_TXID_METRICS,
    STAT_WAL_METRICS,
    WAL_FILE_METRICS,
)
from datadog_checks.postgres.version_utils import VersionUtils

HOST = get_docker_hostname()
PORT = '5432'
PORT_REPLICA = '5433'
PORT_REPLICA2 = '5434'
USER = 'datadog'
USER_ADMIN = 'dd_admin'
PASSWORD = 'datadog'
PASSWORD_ADMIN = 'dd_admin'
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

CONFLICT_METRICS = [
    'postgresql.conflicts.tablespace',
    'postgresql.conflicts.lock',
    'postgresql.conflicts.snapshot',
    'postgresql.conflicts.bufferpin',
    'postgresql.conflicts.deadlock',
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


def _iterate_metric_name(query):
    for column in query['columns']:
        if column['type'].startswith('tag'):
            continue
        yield column['name']


def _get_expected_tags(check, pg_instance, **kwargs):
    base_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'dd.internal.resource:database_instance:{}'.format(check.resolved_hostname),
    ]
    for k, v in kwargs.items():
        base_tags.append('{}:{}'.format(k, v))
    return base_tags


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
            for (metric_name, _) in NEWER_14_METRICS.values():
                aggregator.assert_metric(metric_name, count=count, tags=db_tags)


def check_db_count(aggregator, expected_tags, count=1):
    table_count = 6
    # We create 2 additional partition tables when partition is available
    if float(POSTGRES_VERSION) >= 11.0:
        table_count = 8
    # And PG >= 14 will also report the parent table
    if float(POSTGRES_VERSION) >= 14.0:
        table_count = 9
    aggregator.assert_metric(
        'postgresql.table.count',
        value=table_count,
        count=count,
        tags=expected_tags + ['db:{}'.format(DB_NAME), 'schema:public'],
    )
    aggregator.assert_metric('postgresql.db.count', value=106, count=1)


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
    for metric_name in _iterate_metric_name(QUERY_PG_STAT_WAL_RECEIVER):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_physical_replication_slots(aggregator, expected_tags):
    replication_slot_tags = expected_tags + [
        'slot_name:replication_slot',
        'slot_persistence:permanent',
        'slot_state:active',
        'slot_type:physical',
    ]
    check_replication_slots(aggregator, expected_tags=replication_slot_tags)


def check_logical_replication_slots(aggregator, expected_tags):
    logical_replication_slot_tags = expected_tags + [
        'slot_name:logical_slot',
        'slot_persistence:permanent',
        'slot_state:inactive',
        'slot_type:logical',
    ]
    check_replication_slots(aggregator, expected_tags=logical_replication_slot_tags)


def check_replication_slots(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 10.0:
        return
    for metric_name in _iterate_metric_name(QUERY_PG_REPLICATION_SLOTS):
        if 'slot_type:physical' in expected_tags and metric_name in [
            'postgresql.replication_slot.confirmed_flush_delay_bytes',
        ]:
            continue
        if 'slot_type:logical' in expected_tags and metric_name in [
            'postgresql.replication_slot.restart_delay_bytes',
            'postgresql.replication_slot.xmin_age',
        ]:
            continue
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_replication_delay(aggregator, metrics_cache, expected_tags, count=1):
    replication_metrics = metrics_cache.get_replication_metrics(VersionUtils.parse_version(POSTGRES_VERSION), False)
    for (metric_name, _) in replication_metrics.values():
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_uptime_metrics(aggregator, expected_tags, count=1):
    for metric_name in _iterate_metric_name(QUERY_PG_UPTIME):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_control_metrics(aggregator, expected_tags, count=1):
    for metric_name in _iterate_metric_name(QUERY_PG_CONTROL_CHECKPOINT):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_conflict_metrics(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 9.1:
        return
    for db in COMMON_DBS:
        db_tags = expected_tags + ['db:{}'.format(db)]
        for name in CONFLICT_METRICS:
            aggregator.assert_metric(name, count=count, tags=db_tags)


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


def check_snapshot_txid_metrics(aggregator, expected_tags, count=1):
    for metric_name in _iterate_metric_name(SNAPSHOT_TXID_METRICS):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_file_wal_metrics(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 10:
        return

    for metric_name in _iterate_metric_name(WAL_FILE_METRICS):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)


def check_stat_wal_metrics(aggregator, expected_tags, count=1):
    if float(POSTGRES_VERSION) < 14.0:
        return

    for metric_name in _iterate_metric_name(STAT_WAL_METRICS):
        aggregator.assert_metric(metric_name, count=count, tags=expected_tags)
