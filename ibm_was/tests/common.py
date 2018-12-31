# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from os import path


HERE = path.dirname(path.abspath(__file__))
FIXTURE_DIR = os.path.join(HERE, "fixtures/")

INSTANCE = {
    'servlet_url': 'http://hostname/wasPerfTool/servlet/perfservlet',
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
    'custom_queries': [
        {
            'metric_prefix': 'jdbc_custom',
            'tag_keys':
                [
                    'JDBCKey',
                    'JDBCKey2'
                ],
            'stat': 'JDBC Connection Custom'
        },
        {
            'metric_prefix': 'jvm_custom',
            'tag_keys': [
                'JVMKey'
            ],
            'stat': 'JVM Runtime Custom'
        },
        {
            'metric_prefix': 'object_pool',
            'tag_keys': [
                'implementations'
            ],
            'stat': 'Object Pool'
        }
    ]
}

MISSING_REQ_FIELD_INSTANCE = {
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
}

MALFORMED_CUSTOM_QUERY_INSTANCE = {
    'servlet_url': 'http://hostname/wasPerfTool/servlet/perfservlet',
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
    'custom_queries': [
        {
            'tag_keys':
                [
                    'JDBCKey',
                    'JDBCKey2'
                ],
            'stat': 'JDBC Connection Custom'
        },
    ]
}

METRICS_ALWAYS_PRESENT = [
    'ibmwas.jdbc.CreateCount',
    'ibmwas.jvm.FreeMemory',
    'ibmwas.servlet_session.LifeTime',
    'ibmwas.thread_pools.CreateCount'
]
