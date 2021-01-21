# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import sys

from datadog_checks.sqlserver import SQLServer
from datadog_checks.dev import get_docker_hostname


def lib_tds_path():
    """
    This is definitely ugly but should do the trick most of the times. On OSX
    we can point unixODBC directly to the FreeTDS client library. On linux instead
    we need to define the 'FreeTDS' driver in odbcinst.ini
    """
    if sys.platform == 'darwin':
        return '/usr/local/lib/libtdsodbc.so'
    return 'FreeTDS'


HOST = get_docker_hostname()
PORT = 1433
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_NAME = "sqlserver"

EXPECTED_METRICS = [m[0] for m in SQLServer.METRICS]

INSTANCE_DOCKER = {
    'host': '{},1433'.format(HOST),
    'connector': 'odbc',
    'driver': lib_tds_path(),
    'username': 'sa',
    'password': 'Password123',
    'database': 'master',
    'tags': ['optional:tag1'],
}

INSTANCE_SQL2017 = {
    'host': r'(local)\SQL2017',
    'username': 'sa',
    'password': 'Password12!',
    'database': 'master',
}

INIT_CONFIG = {
    'custom_metrics': [
        {
            'name': 'sqlserver.clr.execution',
            'type': 'gauge',
            'counter_name': 'CLR Execution',
        },
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
    ],
}

INIT_CONFIG_OBJECT_NAME = {
    'custom_metrics': [
        {
            'name': 'sqlserver.cache.hit_ratio',
            'counter_name': 'Cache Hit Ratio',
            'instance_name': 'SQL Plans',
            'object_name': 'SQLServer:Plan Cache',
            'tags': [
                'optional_tag:tag1'
            ]
        },
        {
            'name': 'sqlserver.active_requests',
            'counter_name': 'Active requests',
            'instance_name': 'default',
            'object_name': 'SQLServer:Workload Group Stats',
            'tags': [
                'optional_tag:tag1'
            ]
        }
    ]
}

FULL_CONFIG = {
    "init_config": INIT_CONFIG,
    "instances": [INSTANCE_DOCKER]
}
