# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import common
import tags

MYSQL_MINIMAL_CONFIG = {
    'server': common.HOST,
    'user': common.USER,
    'pass': common.PASS,
    'port': common.PORT
}

MYSQL_COMPLEX_CONFIG = {
    'server': common.HOST,
    'user': common.USER,
    'pass': common.PASS,
    'port': common.PORT,
    'options': {
        'replication': True,
        'extra_status_metrics': True,
        'extra_innodb_metrics': True,
        'extra_performance_metrics': True,
        'schema_size_metrics': True,
    },
    'tags': tags.METRIC_TAGS,
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
    'server': common.HOST,
    'user': 'unknown',
    'pass': common.PASS,
}
