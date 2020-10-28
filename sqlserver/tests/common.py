# (C) Datadog, Inc. 2018-present

# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.utils import ON_MACOS, ON_WINDOWS
from datadog_checks.sqlserver import SQLServer


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
LOCAL_SERVER = 'localhost,{}'.format(PORT)
HERE = get_here()
CHECK_NAME = "sqlserver"

CUSTOM_METRICS = ['sqlserver.clr.execution', 'sqlserver.exec.in_progress']
EXPECTED_METRICS = [
    m[0] for m in SQLServer.INSTANCE_METRICS + SQLServer.TASK_SCHEDULER_METRICS + SQLServer.DATABASE_METRICS
] + CUSTOM_METRICS

EXPECTED_AO_METRICS_PRIMARY = [m[0] for m in SQLServer.AO_METRICS + SQLServer.AO_METRICS_PRIMARY]

EXPECTED_AO_METRICS_SECONDARY = [m[0] for m in SQLServer.AO_METRICS + SQLServer.AO_METRICS_SECONDARY]

INSTANCE_DOCKER = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': get_local_driver(),
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
    'include_task_scheduler_metrics': True,
}

INSTANCE_AO_DOCKER_PRIMARY = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS',
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
    'include_ao_metrics': True,
}

INSTANCE_AO_DOCKER_PRIMARY_NON_EXIST_AG = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS',
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
    'include_ao_metrics': True,
    'availability_group': 'AG2',  # this AG doesn't exist in the setup
}

INSTANCE_AO_DOCKER_PRIMARY_LOCAL_ONLY = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS',
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
    'include_ao_metrics': True,
    'only_emit_local': True,
}

INSTANCE_AO_DOCKER_SECONDARY = {
    'host': '{},1434'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS',
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
    'include_ao_metrics': True,
}

INSTANCE_E2E = INSTANCE_DOCKER.copy()
INSTANCE_E2E['driver'] = 'FreeTDS'

INSTANCE_SQL2017 = {
    'host': LOCAL_SERVER,
    'username': 'sa',
    'password': 'Password12!',
    'connector': 'odbc',
    'driver': '{ODBC Driver 17 for SQL Server}',
    'include_task_scheduler_metrics': True,
}

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
            'name': 'sqlserver.MEMORYCLERK_BITMAP',
            'table': 'sys.dm_os_memory_clerks',
            'counter_name': 'MEMORYCLERK_BITMAP',
            'columns': ['virtual_memory_reserved_kb', 'virtual_memory_committed_kb'],
        },
    ]
}

FULL_E2E_CONFIG = {"init_config": INIT_CONFIG, "instances": [INSTANCE_E2E]}
