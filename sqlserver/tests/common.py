# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev._env import e2e_testing
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
EXPECTED_METRICS = [m[0] for m in SQLServer.METRICS] + CUSTOM_METRICS

INSTANCE_DOCKER = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': 'FreeTDS' if e2e_testing() else get_local_driver(),
    'username': 'sa',
    'password': 'Password123',
    'tags': ['optional:tag1'],
}

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

FULL_CONFIG = {"init_config": INIT_CONFIG, "instances": [INSTANCE_DOCKER]}

E2E_METADATA = {
    # 'start_commands': ['apt-get update', 'apt-get install -y tdsodbc unixodbc-dev'],
    'docker_volumes': [
        '{}:/opt/datadog-agent/embedded/etc/odbcinst.ini'.format(os.path.join(HERE, 'odbc', 'odbcinst.ini'))
    ],
}
