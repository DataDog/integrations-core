# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import itertools
import json
import os
import time
from functools import partial

import mock
import pymongo
import pytest
from bson import Timestamp, json_util
from mock import MagicMock

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
def mock_pymongo():
    mocked_client = MagicMock(
        spec_set=["__getitem__", "server_info", "list_database_names"], name="MockedPyMongoClient"
    )
    with open(os.path.join(common.HERE, "fixtures", "server_info"), 'r') as f:
        mocked_client.server_info = MagicMock(return_value=json.load(f))
    with open(os.path.join(common.HERE, "fixtures", "list_database_names"), 'r') as f:
        mocked_client.list_database_names = MagicMock(return_value=json.load(f))

    def get_collection(self, coll_name):
        if coll_name == "system.replset":
            m = MagicMock(spec_set=["find_one"], name="MockColl<{}:{}>".format(self._db_name, coll_name))
            with open(os.path.join(common.HERE, "fixtures", "find_one_system_replset"), 'r') as f:
                m.find_one = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))
            return m
        elif coll_name in ("oplog.rs", "oplog.$main"):
            m = MagicMock(spec_set=["options", "find"], name="MockColl<{}:{}>".format(self._db_name, coll_name))
            with open(os.path.join(common.HERE, "fixtures", "oplog_rs_options"), 'r') as f:
                m.options = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))

            val1 = [{'ts': Timestamp(1600262019, 1)}]
            val2 = [{'ts': Timestamp(1600327624, 8)}]
            limit = MagicMock(limit=MagicMock(side_effect=itertools.cycle([val1, val2])))
            sort = MagicMock(sort=MagicMock(return_value=limit))
            m.find = MagicMock(return_value=sort)
            return m
        else:
            m = MagicMock(spec_set=['aggregate'])
            with open(os.path.join(common.HERE, "fixtures", "indexStats-{}".format(coll_name)), 'r') as f:
                m.aggregate = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))
            return m

    def mock_command(self, command, *args, **kwargs):
        filename = command
        if command == "dbstats":
            filename += "-{}".format(self._db_name)
        elif command == "collstats":
            coll_name = args[0]
            filename += "-{}".format(coll_name)
        elif command in ("find", "count", "aggregate"):
            # At time of writing, those commands only are for custom queries.
            filename = "custom-query-{}".format(self._query_count)
            self._query_count += 1
        with open(os.path.join(common.HERE, "fixtures", filename), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)

    def get_db(_, db_name):
        mocked_db = MagicMock(
            spec_set=["authenticate", "command", "_db_name", "current_op", "__getitem__", "_query_count"],
            name="MockDB<%s>" % db_name,
        )
        mocked_db._db_name = db_name
        mocked_db.command = partial(mock_command, mocked_db)
        mocked_db.current_op = lambda: mocked_db.command("current_op")
        mocked_db.__getitem__ = get_collection
        mocked_db._query_count = 0
        return mocked_db

    mocked_client.__getitem__ = get_db

    with mock.patch('pymongo.mongo_client.MongoClient', MagicMock(return_value=mocked_client),), mock.patch(
        'pymongo.collection.Collection'
    ), mock.patch('pymongo.command_cursor') as cur:
        cur.CommandCursor = lambda *args, **kwargs: args[1]['firstBatch']
        yield


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
