# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

POSTGRES_INSTANCE = {
    'db_identifier': {
        'host': 'localhost',
        'dbname': 'test_db',
    },
    'port': 5432,
    'username': 'datadog',
    'password': 'datadog',
    'db_type': 'postgres',
    'config_id': 'test-config-123',
    'queries': [
        {
            'monitor_id': 1,
            'query': 'SELECT count(*) FROM orders',
            'interval_seconds': 60,
            'timeout_seconds': 10,
            'entity': {
                'platform': 'aws',
                'account': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'orders',
            },
        },
    ],
}

MULTI_QUERY_INSTANCE = {
    'db_identifier': {
        'host': 'localhost',
        'dbname': 'test_db',
    },
    'port': 5432,
    'username': 'datadog',
    'password': 'datadog',
    'db_type': 'postgres',
    'config_id': 'test-config-multi',
    'queries': [
        {
            'monitor_id': 10,
            'query': 'SELECT count(*) FROM orders',
            'interval_seconds': 60,
            'timeout_seconds': 10,
            'entity': {
                'platform': 'aws',
                'account': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'orders',
            },
        },
        {
            'monitor_id': 20,
            'query': 'SELECT count(*) FROM users',
            'interval_seconds': 120,
            'timeout_seconds': 5,
            'entity': {
                'platform': 'aws',
                'account': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'users',
            },
        },
    ],
}

METRICS = [
    'do_query_actions.query_execution_time',
    'do_query_actions.query_success',
]
