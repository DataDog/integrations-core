# (C) Datadog, Inc. 2018-present

# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import chain

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.utils import ON_MACOS, ON_WINDOWS
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    AO_METRICS,
    AO_METRICS_PRIMARY,
    AO_METRICS_SECONDARY,
    DATABASE_FILES_IO,
    DATABASE_FRAGMENTATION_METRICS,
    DATABASE_MASTER_FILES,
    DATABASE_METRICS,
    DBM_MIGRATED_METRICS,
    INSTANCE_METRICS,
    INSTANCE_METRICS_TOTAL,
    TASK_SCHEDULER_METRICS,
)


def get_local_driver():
    """
    This is definitely ugly but should do the trick most of the times. On OSX
    we can point unixODBC directly to the FreeTDS client library. On linux instead
    we need to define the 'FreeTDS' driver in odbcinst.ini
    """
    if ON_MACOS:
        return '/usr/local/lib/libtdsodbc.so'
    elif ON_WINDOWS:
        return '{ODBC Driver 17 for SQL Server}'
    else:
        return 'FreeTDS'


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
EXPECTED_DEFAULT_METRICS = [
    m[0]
    for m in chain(
        INSTANCE_METRICS,
        DBM_MIGRATED_METRICS,
        INSTANCE_METRICS_TOTAL,
        DATABASE_METRICS,
        DATABASE_FILES_IO,
    )
] + SERVER_METRICS
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

DBM_MIGRATED_METRICS_NAMES = set(m[0] for m in DBM_MIGRATED_METRICS)

EXPECTED_METRICS_DBM_ENABLED = [m for m in EXPECTED_METRICS if m not in DBM_MIGRATED_METRICS_NAMES]

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
EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON = [
    'sqlserver.ao.is_primary_replica',
    'sqlserver.ao.quorum_type',
    'sqlserver.ao.quorum_state',
    'sqlserver.ao.member.type',
    'sqlserver.ao.member.state',
]
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
        'driver': '{ODBC Driver 17 for SQL Server}',
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
            'name': 'sqlserver.active_requests',
            'counter_name': 'Active requests',
            'instance_name': 'default',
            'object_name': 'SQLServer:Workload Group Stats',
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


def assert_metrics(aggregator, expected_tags, dbm_enabled=False, hostname=None, database_autodiscovery=False):
    """
    Boilerplate asserting all the expected metrics and service checks.
    Make sure ALL custom metric is tagged by database.
    """
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    expected_metrics = EXPECTED_METRICS
    if dbm_enabled:
        dbm_excluded_metrics = [m[0] for m in DBM_MIGRATED_METRICS]
        expected_metrics = [m for m in EXPECTED_METRICS if m not in dbm_excluded_metrics]
    for mname in expected_metrics:
        assert hostname is not None, "hostname must be explicitly specified for all metrics"
        aggregator.assert_metric(mname, hostname=hostname)
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    if not database_autodiscovery:
        # if we're autodiscovering other databases then there will be duplicate metrics, one per database
        aggregator.assert_no_duplicate_metrics()
