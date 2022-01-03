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
    DATABASE_FRAGMENTATION_METRICS,
    DATABASE_MASTER_FILES,
    DATABASE_METRICS,
    DBM_MIGRATED_METRICS,
    FCI_METRICS,
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
EXPECTED_DEFAULT_METRICS = [
    m[0]
    for m in chain(
        INSTANCE_METRICS,
        DBM_MIGRATED_METRICS,
        INSTANCE_METRICS_TOTAL,
        DATABASE_METRICS,
    )
]
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

UNEXPECTED_METRICS = FCI_METRICS

EXPECTED_AO_METRICS_PRIMARY = [m[0] for m in AO_METRICS_PRIMARY]
EXPECTED_AO_METRICS_SECONDARY = [m[0] for m in AO_METRICS_SECONDARY]
EXPECTED_AO_METRICS_COMMON = [m[0] for m in AO_METRICS]

INSTANCE_DOCKER_DEFAULTS = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': get_local_driver(),
    'username': 'datadog',
    'password': 'Password12!',
    'disable_generic_tags': True,
    'tags': ['optional:tag1'],
}

INSTANCE_DOCKER = INSTANCE_DOCKER_DEFAULTS.copy()
INSTANCE_DOCKER.update(
    {
        'include_task_scheduler_metrics': True,
        'include_db_fragmentation_metrics': True,
        'include_fci_metrics': True,
        'include_ao_metrics': False,
        'include_master_files_metrics': True,
        'disable_generic_tags': True,
    }
)

INSTANCE_AO_DOCKER_SECONDARY = {
    'host': '{},1434'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS',
    'username': 'datadog',
    'password': 'Password12!',
    'tags': ['optional:tag1'],
    'include_ao_metrics': True,
    'disable_generic_tags': True,
}

CUSTOM_QUERY_A = {
    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
    'tags': ['query:custom'],
}

CUSTOM_QUERY_B = {
    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
    'tags': ['query:another_custom_one'],
}

INSTANCE_E2E = INSTANCE_DOCKER.copy()
INSTANCE_E2E['driver'] = 'FreeTDS'

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

FULL_E2E_CONFIG = {"init_config": INIT_CONFIG, "instances": [INSTANCE_E2E]}


def assert_metrics(aggregator, expected_tags, dbm_enabled=False):
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
        aggregator.assert_metric(mname)
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_metrics()
