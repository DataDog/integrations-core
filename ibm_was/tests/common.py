# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
HOST = get_docker_hostname()
PORT = '9080'

INSTANCE = {
    'servlet_url': 'http://{}:{}/wasPerfTool/servlet/perfservlet'.format(HOST, PORT),
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
    'tags': ['key1:value1'],
    'custom_queries': [
        {'metric_prefix': 'jdbc_custom', 'tag_keys': ['JDBCKey', 'JDBCKey2'], 'stat': 'JDBC Connection Custom'},
        {'metric_prefix': 'jvm_custom', 'tag_keys': ['JVMKey'], 'stat': 'JVM Runtime Custom'},
        {'metric_prefix': 'object_pool', 'tag_keys': ['implementations'], 'stat': 'Object Pool'},
    ],
}

MISSING_REQ_FIELD_INSTANCE = {
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
}

MALFORMED_CUSTOM_QUERY_INSTANCE = {
    'servlet_url': 'http://{}:{}/wasPerfTool/servlet/perfservlet'.format(HOST, PORT),
    'collect_thread_pool_stats': True,
    'collect_servlet_session_stats': True,
    'collect_jdbc_stats': True,
    'custom_queries': [{'tag_keys': ['JDBCKey', 'JDBCKey2'], 'stat': 'JDBC Connection Custom'}],
}

METRICS_ALWAYS_PRESENT = [
    'ibm_was.jdbc.percent_used',
    'ibm_was.jvm.heap_size',
    'ibm_was.servlet_session.live_count',
    'ibm_was.thread_pools.pool_size',
]

DEFAULT_SERVICE_CHECK_TAGS = ['url:{}'.format(INSTANCE.get('servlet_url')), 'key1:value1']
