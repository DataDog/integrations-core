# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from os import path


HERE = path.dirname(path.abspath(__file__))
FIXTURE_DIR = os.path.join(HERE, "fixtures/")

INSTANCE = {
    'servlet_url': 'http://hostname/wasPerfTool/servlet/perfservlet',
    'collect_thread_pool_stats': False,
    'collect_servlet_session_stats': False,
    'collect_jdbc_stats': False,
    'custom_queries': [
        {
            'metric_prefix': 'jdbc_custom',
            'tagKeys':
                [
                    'JDBCKey',
                    'JDBCKey2'
                ],
            'stat': 'JDBC Connection Custom'
        },
        {
            'metric_prefix': 'jvm_custom',
            'tagKeys': [
                'JVMKey'
            ],
            'stat': 'JVM Runtime Custom'
        }
    ]
}
