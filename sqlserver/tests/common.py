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

CUSTOM_METRICS = [
                   'sqlserver.clr.execution',
                   'sqlserver.exec.in_progress',
                   'sqlserver.scheduler.current_workers_count',
                   'sqlserver.scheduler.active_workers_count',
                   'sqlserver.scheduler.current_tasks_count',
                   'sqlserver.scheduler.runnable_tasks_count',
                   'sqlserver.scheduler.work_queue_count',
                   'sqlserver.task.context_switches_count',
                   'sqlserver.task.pending_io_count',
                   'sqlserver.task.pending_io_byte_count',
                   'sqlserver.task.pending_io_byte_average',
                 ]
EXPECTED_METRICS = [m[0] for m in SQLServer.METRICS] + CUSTOM_METRICS
DM_OS_SCHEDULERS = "sys.dm_os_schedulers"
DM_OS_TASKS = "sys.dm_os_tasks"

INSTANCE_DOCKER = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': get_local_driver(),
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
}

INSTANCE_E2E = INSTANCE_DOCKER.copy()
INSTANCE_E2E['driver'] = 'FreeTDS'

INSTANCE_SQL2017 = {
    'host': LOCAL_SERVER,
    'username': 'sa',
    'password': 'Password12!',
    'connector': 'odbc',
    'driver': '{ODBC Driver 17 for SQL Server}',
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
        {
            'name': 'sqlserver.scheduler',
            'table': DM_OS_SCHEDULERS,
            'type': 'gauge',
            'columns': ['current_workers_count', 'active_workers_count', 'current_tasks_count', 'runnable_tasks_count', 'work_queue_count', 'num_reads'],
            'instance_name': 'ALL',
            'tag_by': 'db',
        },
        {
            'name': 'sqlserver.task',
            'table': DM_OS_TASKS,
            'type': 'gauge',
            'columns': ['context_switches_count', 'pending_io_count', 'pending_io_byte_count', 'pending_io_byte_average'],
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

FULL_E2E_CONFIG = {"init_config": INIT_CONFIG, "instances": [INSTANCE_E2E]}
