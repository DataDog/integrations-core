# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

POSTGRES_INSTANCE = {
    'host': 'localhost',
    'port': 5432,
    'username': 'datadog',
    'password': 'datadog',
    'dbname': 'test_db',
    'db_type': 'postgres',
    'remote_config_id': 'test-config-123',
    'queries': [
        {
            'monitor_id': 1,
            'query': 'SELECT count(*) FROM orders',
            'interval_seconds': 60,
            'timeout_seconds': 10,
            'entity': {
                'platform': 'aws',
                'account_id': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'orders',
                'metric_config_id': 100,
                'measure': 'row_count',
            },
        },
    ],
}

MULTI_QUERY_INSTANCE = {
    'host': 'localhost',
    'port': 5432,
    'username': 'datadog',
    'password': 'datadog',
    'dbname': 'test_db',
    'db_type': 'postgres',
    'remote_config_id': 'test-config-multi',
    'queries': [
        {
            'monitor_id': 10,
            'query': 'SELECT count(*) FROM orders',
            'interval_seconds': 60,
            'timeout_seconds': 10,
            'entity': {
                'platform': 'aws',
                'account_id': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'orders',
                'metric_config_id': 100,
                'measure': 'row_count',
            },
        },
        {
            'monitor_id': 20,
            'query': 'SELECT count(*) FROM users',
            'interval_seconds': 120,
            'timeout_seconds': 5,
            'entity': {
                'platform': 'aws',
                'account_id': '123456',
                'database': 'test_db',
                'schema': 'public',
                'table': 'users',
                'metric_config_id': 101,
                'measure': 'row_count',
            },
        },
    ],
}

METRICS = [
    'do_query_actions.query_execution_time',
    'do_query_actions.query_success',
]
