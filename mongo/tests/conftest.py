# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time

import pymongo
import pytest

from datadog_checks.dev import LazyFunction, WaitFor, docker_run, run_command
from datadog_checks.mongo import MongoDb

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yml')

    with docker_run(
        compose_file, conditions=[WaitFor(setup_sharding, args=(compose_file,), attempts=5, wait=5), InitializeDB()]
    ):
        yield common.INSTANCE_BASIC


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE_BASIC)


@pytest.fixture
def instance_user():
    return copy.deepcopy(common.INSTANCE_USER)


@pytest.fixture
def instance_authdb():
    return copy.deepcopy(common.INSTANCE_AUTHDB)


@pytest.fixture
def instance_custom_queries():
    instance = copy.deepcopy(common.INSTANCE_USER)
    instance['custom_queries'] = [
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
            'fields': [
                {'field_name': 'total', 'name': 'total', 'type': 'count'},
                {'field_name': '_id', 'name': 'cluster_id', 'type': 'tag'},
            ],
            'metric_prefix': 'dd.custom.mongo.aggregate',
            'tags': ['tag1:val1', 'tag2:val2'],
        },
    ]

    return instance


@pytest.fixture
def instance_1valid_and_1invalid_custom_queries():
    instance = copy.deepcopy(common.INSTANCE_USER)
    instance['custom_queries'] = [
        {
            'metric_prefix': 'dd.custom.mongo.count',
            # invalid query with missing query, skipped with error/warning logs
        },
        {
            'query': {'count': 'foo', 'query': {'1': {'$type': 16}}},
            'metric_prefix': 'dd.custom.mongo.count',
            'tags': ['tag1:val1', 'tag2:val2'],
            'count_type': 'gauge',
        },
    ]

    return instance


@pytest.fixture
def check():
    return lambda instance: MongoDb('mongo', {}, [instance])


def setup_sharding(compose_file):
    service_commands = [
        ('config01', 'mongo --port 27017 < /scripts/init-configserver.js'),
        ('shard01a', 'mongo --port 27018 < /scripts/init-shard01.js'),
        ('shard02a', 'mongo --port 27019 < /scripts/init-shard02.js'),
        ('shard03a', 'mongo --port 27020 < /scripts/init-shard03.js'),
        ('router', 'mongo < /scripts/init-router.js'),
    ]

    for i, (service, command) in enumerate(service_commands, 1):
        # Wait before router init
        if i == len(service_commands):
            time.sleep(20)

        run_command(['docker-compose', '-f', compose_file, 'exec', '-T', service, 'sh', '-c', command], check=True)


class InitializeDB(LazyFunction):
    def __call__(self):
        cli = pymongo.mongo_client.MongoClient(
            common.MONGODB_SERVER, socketTimeoutMS=30000, read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED
        )

        foos = []
        for i in range(70):
            foos.append({'1': []})
            foos.append({'1': i})
            foos.append({})

        bars = []
        for _ in range(50):
            bars.append({'1': []})
            bars.append({})

        orders = [
            {"cust_id": "abc1", "status": "A", "amount": 50, "elements": 3},
            {"cust_id": "xyz1", "status": "A", "amount": 100},
            {"cust_id": "abc1", "status": "D", "amount": 50, "elements": 1},
            {"cust_id": "abc1", "status": "A", "amount": 25},
            {"cust_id": "xyz1", "status": "A", "amount": 25},
            {"cust_id": "abc1", "status": "A", "amount": 300, "elements": 10},
        ]

        db = cli['test']
        db.foo.insert_many(foos)
        db.bar.insert_many(bars)
        db.orders.insert_many(orders)

        auth_db = cli['authDB']
        auth_db.command("createUser", 'testUser', pwd='testPass', roles=[{'role': 'read', 'db': 'test'}])
        auth_db.command("createUser", 'special test user', pwd='s3\\kr@t', roles=[{'role': 'read', 'db': 'test'}])

        db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': 'test'}])
