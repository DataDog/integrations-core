# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT1 = 27017
PORT2 = 27018
PORT_ARBITER = 27020
MAX_WAIT = 150

COMPOSE_FILE = os.getenv('COMPOSE_FILE')
IS_STANDALONE = COMPOSE_FILE == 'mongo-standalone.yaml'
IS_SHARD = COMPOSE_FILE == 'mongo-shard.yaml'
IS_TLS = COMPOSE_FILE == 'mongo-tls.yaml'
IS_AUTH = COMPOSE_FILE == 'mongo-auth.yaml'

TLS_CERTS_FOLDER = os.path.join(os.path.dirname(__file__), 'compose', 'certs')

standalone = pytest.mark.skipif(not IS_STANDALONE, reason='Test only valid for standalone mongo')
shard = pytest.mark.skipif(not IS_SHARD, reason='Test only valid for sharded mongo')
tls = pytest.mark.skipif(not IS_TLS, reason='Test only valid for TLS')
auth = pytest.mark.skipif(not IS_AUTH, reason='Test only valid for mongo with --auth')

MONGODB_VERSION = os.environ['MONGO_VERSION']

ROOT = os.path.dirname(os.path.dirname(HERE))

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT1)]}
INSTANCE_BASIC_SHARD = {'hosts': ['{}:{}'.format(HOST, PORT2)]}
INSTANCE_BASIC_LEGACY_CONFIG = {'server': "mongodb://%s:%s/test" % (HOST, PORT1)}

INSTANCE_AUTHDB = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser',
    'password': 'testPass',
    'options': {'authSource': 'authDB'},
}
INSTANCE_AUTHDB_ALT = {
    # Include special cases, e.g. default port and special characters
    'hosts': [HOST],
    'database': 'test',
    'username': 'special test user',
    'password': 's3\\kr@t',
    'options': {'authSource': 'authDB'},
}
INSTANCE_AUTHDB_LEGACY_CONFIG = {
    'server': 'mongodb://testUser:testPass@{}:{}/test?authSource=authDB'.format(HOST, PORT1)
}

INSTANCE_USER = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
}
INSTANCE_USER_LEGACY_CONFIG = {'server': 'mongodb://testUser2:testPass2@{}:{}/test'.format(HOST, PORT1)}

INSTANCE_ARBITER = {'hosts': ['{}:{}'.format(HOST, PORT_ARBITER)]}

INSTANCE_CUSTOM_QUERIES = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
    'custom_queries': [
        {
            'metric_prefix': 'dd.custom.mongo.query_a',
            'query': {'find': 'orders', 'filter': {'amount': {'$gt': 25}}, 'sort': {'amount': -1}},
            'fields': [
                {'field_name': 'cust_id', 'name': 'cluster_id', 'type': 'tag'},
                {'field_name': 'status', 'name': 'status_tag', 'type': 'tag'},
                {'field_name': 'amount', 'name': 'amount', 'type': 'count'},
                {'field_name': 'elements', 'name': 'el', 'type': 'count'},
            ],
            'tags': ['tag1:val1', 'tag2:val2'],
        },
        {
            'query': {'count': 'foo', 'query': {'1': {'$type': 16}}},
            'database': 'test',
            'metric_prefix': 'dd.custom.mongo.count',
            'tags': ['tag1:val1', 'tag2:val2'],
            'count_type': 'gauge',
        },
        {
            'query': {
                'aggregate': 'orders',
                'pipeline': [
                    {'$match': {'status': 'A'}},
                    {'$group': {'_id': '$cust_id', 'total': {'$sum': '$amount'}}},
                    {'$sort': {'total': -1}},
                ],
                'cursor': {},
            },
            'database': 'test2',
            'fields': [
                {'field_name': 'total', 'name': 'total', 'type': 'count'},
                {'field_name': '_id', 'name': 'cluster_id', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.custom.mongo.aggregate',
            'tags': ['tag1:val1', 'tag2:val2'],
        },
        {
            'query': {
                'aggregate': 1,
                'pipeline': [
                    {'$currentOp': {'allUsers': True}},
                ],
                'cursor': {},
            },
            'database': 'admin',
            'fields': [
                {'field_name': 'secs_running', 'name': 'secs_running', 'type': 'gauge'},
                {'field_name': 'appName', 'name': 'app_name', 'type': 'tag'},
                {'field_name': 'ns', 'name': 'mongo_op_namespace', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.mongodb.custom.queries_slower_than_60sec',
            'tags': ['tag1:val1', 'tag2:val2'],
        },
    ],
}

INSTANCE_CUSTOM_QUERIES_WITH_DATE = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
    'custom_queries': [
        {
            'query': {
                'aggregate': 'orders',
                'pipeline': [
                    {
                        '$match': {
                            'status': 'A',
                            "created_time": {
                                "$gte": "new Date(ISODate().getTime() - 60000)",
                                "$lt": "Date()",
                            },
                        }
                    },
                    {'$group': {'_id': '$cust_id', 'total': {'$sum': '$amount'}}},
                    {'$sort': {'total': -1}},
                ],
                'cursor': {},
            },
            'database': 'test2',
            'fields': [
                {'field_name': 'total', 'name': 'total', 'type': 'count'},
                {'field_name': '_id', 'name': 'cluster_id', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.custom.mongo.aggregate',
            'tags': ['tag1:val1', 'tag2:val2'],
        }
    ],
}

INSTANCE_CUSTOM_QUERIES_WITH_DATE_AND_OPERATION = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
    'custom_queries': [
        {
            'query': {
                'aggregate': 'orders',
                'pipeline': [
                    {
                        '$match': {
                            'status': 'A',
                            "created_time": {
                                "$gte": "new Date(ISODate().getTime() - 60 * 1000)",
                                "$lt": "Date()",
                            },
                        }
                    },
                    {'$group': {'_id': '$cust_id', 'total': {'$sum': '$amount'}}},
                    {'$sort': {'total': -1}},
                ],
                'cursor': {},
            },
            'database': 'test2',
            'fields': [
                {'field_name': 'total', 'name': 'total', 'type': 'count'},
                {'field_name': '_id', 'name': 'cluster_id', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.custom.mongo.aggregate',
            'tags': ['tag1:val1', 'tag2:val2'],
        }
    ],
}

INSTANCE_CUSTOM_QUERIES_WITH_ISODATE = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
    'custom_queries': [
        {
            'query': {
                'aggregate': 'orders',
                'pipeline': [
                    {
                        '$match': {
                            'status': 'A',
                            "created_time": {
                                "$gte": "ISODate('2000-01-01T00:00:00.000+0000')",
                                "$lt": "ISODate()",
                            },
                        }
                    },
                    {'$group': {'_id': '$cust_id', 'total': {'$sum': '$amount'}}},
                    {'$sort': {'total': -1}},
                ],
                'cursor': {},
            },
            'database': 'test2',
            'fields': [
                {'field_name': 'total', 'name': 'total', 'type': 'count'},
                {'field_name': '_id', 'name': 'cluster_id', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.custom.mongo.aggregate',
            'tags': ['tag1:val1', 'tag2:val2'],
        }
    ],
}

INSTANCE_CUSTOM_QUERIES_WITH_STRING_LIST = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
    'custom_queries': [
        {
            'metric_prefix': 'dd.custom.mongo.string',
            'query': {
                'find': 'orders',
                'filter': {'amount': {'$gt': 25}},
                'sort': {'amount': -1},
                'projection': {'result': {'$subtract': ['$amount', 1]}},
            },
            'fields': [
                {'field_name': 'result', 'name': 'result', 'type': 'gauge'},
            ],
        },
    ],
}

TLS_METADATA = {
    'docker_volumes': [
        '{}:/certs'.format(TLS_CERTS_FOLDER),
    ],
}
