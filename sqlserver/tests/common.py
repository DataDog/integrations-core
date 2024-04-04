# (C) Datadog, Inc. 2018-present

# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy
from itertools import chain

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.utils import ON_MACOS, ON_WINDOWS
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    AO_METRICS,
    AO_METRICS_PRIMARY,
    AO_METRICS_SECONDARY,
    DATABASE_BACKUP_METRICS,
    DATABASE_FRAGMENTATION_METRICS,
    DATABASE_INDEX_METRICS,
    DATABASE_MASTER_FILES,
    DATABASE_METRICS,
    DBM_MIGRATED_METRICS,
    INSTANCE_METRICS,
    INSTANCE_METRICS_DATABASE_AO,
    INSTANCE_METRICS_DATABASE_SINGLE,
    TASK_SCHEDULER_METRICS,
    TEMPDB_FILE_SPACE_USAGE_METRICS,
)
from datadog_checks.sqlserver.queries import get_query_file_stats

from .utils import is_always_on


def get_local_driver():
    """
    This is definitely ugly but should do the trick most of the times. On OSX
    we can point unixODBC directly to the FreeTDS client library. On linux instead
    we need to define the 'FreeTDS' driver in odbcinst.ini
    """
    if ON_MACOS:
        return '/usr/local/lib/libtdsodbc.so'
    elif ON_WINDOWS:
        return '{ODBC Driver 18 for SQL Server}'
    else:
        return '{ODBC Driver 18 for SQL Server}'


HOST = get_docker_hostname()
PORT = 1433
DOCKER_SERVER = '{},{}'.format(HOST, PORT)
HERE = get_here()
CHECK_NAME = "sqlserver"

CUSTOM_METRICS = ['sqlserver.clr.execution', 'sqlserver.db.commit_table_entries', 'sqlserver.exec.in_progress']
SERVER_METRICS = [
    'sqlserver.server.committed_memory',
    'sqlserver.server.cpu_count',
    'sqlserver.server.physical_memory',
    'sqlserver.server.target_memory',
    'sqlserver.server.uptime',
    'sqlserver.server.virtual_memory',
]

SQLSERVER_MAJOR_VERSION = int(os.environ.get('SQLSERVER_MAJOR_VERSION'))
SQLSERVER_ENGINE_EDITION = int(os.environ.get('SQLSERVER_ENGINE_EDITION'))


def get_expected_file_stats_metrics():
    query_file_stats = get_query_file_stats(SQLSERVER_MAJOR_VERSION, SQLSERVER_ENGINE_EDITION)
    return ["sqlserver." + c["name"] for c in query_file_stats["columns"] if c["type"] != "tag"]


EXPECTED_FILE_STATS_METRICS = get_expected_file_stats_metrics()

# SQL Server incremental sql fraction metrics require diffs in order to calculate
# & report the metric, which means this requires a special unit/integration test coverage
inc_perf_counter_metrics = [
    ('sqlserver.latches.latch_wait_time', 'Average Latch Wait Time (ms)', ''),
]

EXPECTED_INSTANCE_METRICS = [metric for metric in INSTANCE_METRICS if metric not in inc_perf_counter_metrics]

EXPECTED_DEFAULT_METRICS = (
    [
        m[0]
        for m in chain(
            EXPECTED_INSTANCE_METRICS,
            DBM_MIGRATED_METRICS,
            INSTANCE_METRICS_DATABASE_SINGLE,
            DATABASE_METRICS,
            DATABASE_BACKUP_METRICS,
            TEMPDB_FILE_SPACE_USAGE_METRICS,
        )
    ]
    + DATABASE_INDEX_METRICS
    + SERVER_METRICS
    + EXPECTED_FILE_STATS_METRICS
)
EXPECTED_METRICS = (
    EXPECTED_DEFAULT_METRICS
    + [
        m[0]
        for m in chain(
            TASK_SCHEDULER_METRICS,
            DATABASE_FRAGMENTATION_METRICS,
            DATABASE_MASTER_FILES,
        )
    ]
    + CUSTOM_METRICS
)

DBM_MIGRATED_METRICS_NAMES = {m[0] for m in DBM_MIGRATED_METRICS}
EXPECTED_METRICS_DBM_ENABLED = [m for m in EXPECTED_METRICS if m not in DBM_MIGRATED_METRICS_NAMES]
DB_PERF_COUNT_METRICS_NAMES_SINGLE = {m[0] for m in INSTANCE_METRICS_DATABASE_SINGLE}
DB_PERF_COUNT_METRICS_NAMES_AO = {m[0] for m in INSTANCE_METRICS_DATABASE_AO}

# These AO metrics are collected using the new QueryExecutor API instead of BaseSqlServerMetric.
EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY = [
    'sqlserver.ao.low_water_mark_for_ghosts',
    'sqlserver.ao.secondary_lag_seconds',
]
EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY = [
    'sqlserver.ao.log_send_queue_size',
    'sqlserver.ao.log_send_rate',
    'sqlserver.ao.redo_queue_size',
    'sqlserver.ao.redo_rate',
    'sqlserver.ao.filestream_send_rate',
]
EXPECTED_QUERY_EXECUTOR_AO_METRICS_REPLICA_COMMON = [
    'sqlserver.ao.is_primary_replica',
    'sqlserver.ao.replica_status',
]
EXPECTED_QUERY_EXECUTOR_AO_METRICS_QUORUM_COMMON = [
    'sqlserver.ao.quorum_type',
    'sqlserver.ao.quorum_state',
]
EXPECTED_QUERY_EXECUTOR_AO_METRICS_MEMBER_COMMON = [
    'sqlserver.ao.member.type',
    'sqlserver.ao.member.state',
]
EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON = (
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_REPLICA_COMMON
    + EXPECTED_QUERY_EXECUTOR_AO_METRICS_QUORUM_COMMON
    + EXPECTED_QUERY_EXECUTOR_AO_METRICS_MEMBER_COMMON
)

# Our test environment does not have failover clustering enabled, so these metrics are not expected.
# To test them follow this guide:
# https://cloud.google.com/compute/docs/instances/sql-server/configure-failover-cluster-instance
UNEXPECTED_QUERY_EXECUTOR_AO_METRICS = ['sqlserver.ao.member.number_of_quorum_votes']
UNEXPECTED_FCI_METRICS = [
    'sqlserver.fci.status',
    'sqlserver.fci.is_current_owner',
]

EXPECTED_AO_METRICS_PRIMARY = [m[0] for m in AO_METRICS_PRIMARY]
EXPECTED_AO_METRICS_SECONDARY = [m[0] for m in AO_METRICS_SECONDARY]
EXPECTED_AO_METRICS_COMMON = [m[0] for m in AO_METRICS]

INSTANCE_SQL_DEFAULTS = {
    'host': DOCKER_SERVER,
    'username': 'sa',
    'password': 'Password12!',
    'disable_generic_tags': True,
}
INSTANCE_SQL = INSTANCE_SQL_DEFAULTS.copy()
INSTANCE_SQL.update(
    {
        'connector': 'odbc',
        'driver': '{ODBC Driver 18 for SQL Server}',
        'include_task_scheduler_metrics': True,
        'include_db_fragmentation_metrics': True,
        'include_fci_metrics': True,
        'include_ao_metrics': False,
        'include_master_files_metrics': True,
        'disable_generic_tags': True,
    }
)

INIT_CONFIG = {
    'custom_metrics': [
        {'name': 'sqlserver.clr.execution', 'type': 'gauge', 'counter_name': 'CLR Execution'},
        {
            'name': 'sqlserver.exec.in_progress',
            'type': 'gauge',
            'counter_name': 'OLEDB calls',
            'instance_name': 'Cumulative execution time (ms) per second',
        },
        {
            'name': 'sqlserver.db.commit_table_entries',
            'type': 'gauge',
            'counter_name': 'Log Flushes/sec',
            'instance_name': 'ALL',
            'tag_by': 'db',
        },
    ]
}

INIT_CONFIG_OBJECT_NAME = {
    'custom_metrics': [
        {
            'name': 'sqlserver.cache.hit_ratio',
            'counter_name': 'Cache Hit Ratio',
            'instance_name': 'SQL Plans',
            'object_name': 'SQLServer:Plan Cache',
            'tags': ['optional_tag:tag1'],
        },
        {
            'name': 'sqlserver.broker_activation.tasks_running',
            'counter_name': 'Tasks Running',
            'instance_name': 'tempdb',
            'object_name': 'SQLServer:Broker Activation',
            'tags': ['optional_tag:tag1'],
        },
    ]
}

# As documented here: https://docs.datadoghq.com/integrations/guide/collect-sql-server-custom-metrics/
INIT_CONFIG_ALT_TABLES = {
    'custom_metrics': [
        {
            'name': 'sqlserver.LCK_M_S',
            'table': 'sys.dm_os_wait_stats',
            'counter_name': 'LCK_M_S',
            'columns': ['max_wait_time_ms', 'signal_wait_time_ms'],
        },
        {
            'name': 'sqlserver.io_file_stats',
            'table': 'sys.dm_io_virtual_file_stats',
            'columns': ['num_of_reads', 'num_of_writes'],
        },
        {
            'name': 'sqlserver.MEMORYCLERK_SQLGENERAL',
            'table': 'sys.dm_os_memory_clerks',
            'counter_name': 'MEMORYCLERK_SQLGENERAL',
            'columns': ['virtual_memory_reserved_kb', 'virtual_memory_committed_kb'],
        },
    ]
}

OPERATION_TIME_METRICS = [
    'simple_metrics',
    'database_stats_metrics',
    'fraction_metrics',
    'db_file_space_usage_metrics',
    'database_backup_metrics',
    'database_file_stats_metrics',
    'incr_fraction_metrics',
]

OPERATION_TIME_METRIC_NAME = 'dd.sqlserver.operation.time'

E2E_OPERATION_TIME_METRIC_NAME = [
    'dd.sqlserver.operation.time.{}'.format(suffix) for suffix in ('avg', 'max', '95percentile', 'count', 'median')
]


def assert_metrics(
    instance,
    aggregator,
    check_tags,
    service_tags,
    dbm_enabled=False,
    hostname=None,
    database_autodiscovery=False,
    dbs=None,
):
    """
    Boilerplate asserting all the expected metrics and service checks.
    Make sure ALL custom metric is tagged by database.
    """
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    expected_metrics = EXPECTED_METRICS
    # if dbm is enabled, the integration does not emit certain metrics
    # as they are emitted from the DBM backend
    if dbm_enabled:
        expected_metrics = [m for m in expected_metrics if m not in DBM_MIGRATED_METRICS_NAMES]

    if database_autodiscovery:
        # when autodiscovery is enabled, we should not double emit metrics,
        # so we should assert for these separately with the proper tags
        expected_metrics = [m for m in expected_metrics if m not in DB_PERF_COUNT_METRICS_NAMES_SINGLE]

        for dbname in dbs:
            tags = check_tags + ['database:{}'.format(dbname)]
            for mname in DB_PERF_COUNT_METRICS_NAMES_SINGLE:
                aggregator.assert_metric(mname, hostname=hostname, tags=tags)
            if dbname == 'datadog_test' and is_always_on():
                for mname in DB_PERF_COUNT_METRICS_NAMES_AO:
                    aggregator.assert_metric(mname, hostname=hostname, tags=tags)
    else:
        # master does not have indexes so none of these metrics will be emitted
        expected_metrics = [m for m in expected_metrics if m not in DATABASE_INDEX_METRICS]
    for mname in expected_metrics:
        assert hostname is not None, "hostname must be explicitly specified for all metrics"
        aggregator.assert_metric(mname, hostname=hostname)
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=service_tags)

    operation_time_metric_tags = check_tags + ['agent_hostname:{}'.format(hostname)]
    for operation_name in get_operation_time_metrics(instance):
        aggregator.assert_metric(
            OPERATION_TIME_METRIC_NAME,
            tags=['operation:{}'.format(operation_name)] + operation_time_metric_tags,
            hostname=hostname,
            count=1,
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_metrics()


def get_operation_time_metrics(instance):
    """
    Return a list of all operation time metrics
    """
    operation_time_metrics = deepcopy(OPERATION_TIME_METRICS)
    if instance.get('include_task_scheduler_metrics', False):
        operation_time_metrics.append('os_schedulers_metrics')
        operation_time_metrics.append('os_tasks_metrics')
    if instance.get('include_db_fragmentation_metrics', False):
        operation_time_metrics.append('db_fragmentation_metrics')
    if instance.get('include_ao_metrics', False):
        operation_time_metrics.append('availability_groups_metrics')
    if instance.get('include_master_files_metrics', False):
        operation_time_metrics.append('master_database_file_stats_metrics')
    return operation_time_metrics
