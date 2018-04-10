# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import variables

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog-checks-tests-helper')

CHECK_NAME = 'mysql'

HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
PORT = 13306
SLAVE_PORT = 13307

USER = 'dog'
PASS = 'dog'

MYSQL_MINIMAL_CONFIG = {
    'server': HOST,
    'user': USER,
    'pass': PASS,
    'port': PORT
}

MYSQL_COMPLEX_CONFIG = {
    'server': HOST,
    'user': USER,
    'pass': PASS,
    'port': PORT,
    'options': {
        'replication': True,
        'extra_status_metrics': True,
        'extra_innodb_metrics': True,
        'extra_performance_metrics': True,
        'schema_size_metrics': True,
    },
    'tags': variables.METRIC_TAGS,
    'queries': [
        {
            'query': "SELECT * from testdb.users where name='Alice' limit 1;",
            'metric': 'alice.age',
            'type': 'gauge',
            'field': 'age'
        },
        {
            'query': "SELECT * from testdb.users where name='Bob' limit 1;",
            'metric': 'bob.age',
            'type': 'gauge',
            'field': 'age'
        }
    ]
}

CONNECTION_FAILURE = {
    'server': HOST,
    'user': 'unknown',
    'pass': PASS,
}
