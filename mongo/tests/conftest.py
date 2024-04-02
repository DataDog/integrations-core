# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time
from contextlib import contextmanager
from datetime import datetime

import mock
import pymongo
import pytest
from datadog_test_libs.utils.mock_dns import mock_local
from dateutil.tz import tzutc
from packaging import version

from datadog_checks.dev import LazyFunction, WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import WaitForPortListening
from datadog_checks.mongo import MongoDb
from tests.mocked_api import MockedPyMongoClient

from . import common
from .common import MONGODB_VERSION

HOSTNAME_TO_PORT_MAPPING = {
    "shard01a": (
        '127.0.0.1',
        27018,
    ),
    "shard01b": (
        '127.0.0.1',
        27019,
    ),
    "shard01c": (
        '127.0.0.1',
        27020,
    ),
}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'compose', common.COMPOSE_FILE)

    if common.IS_AUTH:
        conditions = [
            WaitForPortListening(common.HOST, common.PORT1),
            InitializeAuthDB(),
        ]
        with docker_run(
            compose_file,
            conditions=conditions,
        ):
            yield common.INSTANCE_BASIC, {}
    elif common.IS_TLS:
        conditions = [WaitForPortListening(common.HOST, common.PORT1)]
        with docker_run(
            compose_file,
            conditions=conditions,
        ):
            yield common.INSTANCE_BASIC, common.TLS_METADATA
    elif common.IS_STANDALONE:
        conditions = [
            WaitForPortListening(common.HOST, common.PORT1),
            InitializeDB(),
        ]
        with docker_run(
            compose_file,
            conditions=conditions,
        ):
            yield common.INSTANCE_BASIC, {}
    elif common.IS_SHARD:
        conditions = [
            WaitFor(setup_sharding, args=(compose_file,), attempts=5, wait=5),
            InitializeDB(),
        ]
        with docker_run(
            compose_file,
            conditions=conditions,
        ):
            yield common.INSTANCE_CUSTOM_QUERIES, {'custom_hosts': get_custom_hosts()}


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in HOSTNAME_TO_PORT_MAPPING]


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE_BASIC)


@pytest.fixture
def instance_shard():
    return copy.deepcopy(common.INSTANCE_BASIC_SHARD)


@pytest.fixture
def instance_user():
    return copy.deepcopy(common.INSTANCE_USER)


@pytest.fixture
def instance_authdb():
    return copy.deepcopy(common.INSTANCE_AUTHDB)


@pytest.fixture
def instance_dbstats_tag_dbname():
    return copy.deepcopy(common.INSTANCE_DBSTATS_TAG_DBNAME)


@pytest.fixture
def instance_custom_queries():
    return copy.deepcopy(common.INSTANCE_CUSTOM_QUERIES)


@pytest.fixture
def instance_integration(instance_custom_queries):
    instance = copy.deepcopy(instance_custom_queries)
    instance["additional_metrics"] = ["metrics.commands", "tcmalloc", "collection", "top", "jumbo_chunks"]
    instance["collections"] = ["foo", "bar"]
    instance["collections_indexes_stats"] = True
    instance["add_node_tag_to_events"] = False
    return instance


@pytest.fixture(scope='session', autouse=True)
def mock_local_tls_dns():
    with mock_local(HOSTNAME_TO_PORT_MAPPING):
        yield


@contextmanager
def mock_pymongo(deployment):
    mocked_client = MockedPyMongoClient(deployment=deployment)
    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)), mock.patch(
        'pymongo.collection.Collection'
    ), mock.patch('pymongo.command_cursor') as cur:
        cur.CommandCursor = lambda *args, **kwargs: args[1]['firstBatch']
        yield mocked_client


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
def instance_arbiter():
    return common.INSTANCE_ARBITER.copy()


@pytest.fixture
def check():
    return lambda instance: MongoDb('mongo', {}, [instance])


def setup_sharding(compose_file):
    command = 'mongo' if version.parse(MONGODB_VERSION) < version.parse('6.0') else 'mongosh'
    service_commands = [
        ('config01', f'{command} --port 27017 < /scripts/init-configserver.js'),
        ('shard01a', f'{command} --port 27018 < /scripts/init-shard01.js'),
        ('shard02a', f'{command} --port 27019 < /scripts/init-shard02.js'),
        ('shard03a', f'{command} --port 27020 < /scripts/init-shard03.js'),
        ('router', f'{command} < /scripts/init-router.js'),
    ]

    for i, (service, command) in enumerate(service_commands, 1):
        # Wait before router init
        if i == len(service_commands):
            time.sleep(10)

        run_command(['docker', 'compose', '-f', compose_file, 'exec', '-T', service, 'sh', '-c', command], check=True)


class InitializeDB(LazyFunction):
    def __call__(self):
        cli = pymongo.mongo_client.MongoClient(
            f"mongodb://{common.HOST}:{common.PORT1}",
            socketTimeoutMS=30000,
            read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,
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
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "abc1", "status": "A", "amount": 50, "elements": 3},
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "xyz1", "status": "A", "amount": 100},
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "abc1", "status": "D", "amount": 50, "elements": 1},
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "abc1", "status": "A", "amount": 25},
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "xyz1", "status": "A", "amount": 25},
            {'created_time': datetime.now(tz=tzutc()), "cust_id": "abc1", "status": "A", "amount": 300, "elements": 10},
        ]

        for db_name in ['test', 'test2', 'admin']:
            db = cli[db_name]
            db.foo.insert_many(foos)
            db.bar.insert_many(bars)
            db.orders.insert_many(orders)
            db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': db_name}])

        cli['admin'].command(
            "createUser",
            'testUser',
            pwd='testPass',
            roles=[
                {'role': 'read', 'db': 'test'},
                {'role': "clusterManager", 'db': "admin"},
                {'role': "clusterMonitor", 'db': "admin"},
            ],
        )
        auth_db = cli['authDB']
        auth_db.command("createUser", 'testUser', pwd='testPass', roles=[{'role': 'read', 'db': 'test'}])
        auth_db.command("createUser", 'special test user', pwd='s3\\kr@t', roles=[{'role': 'read', 'db': 'test'}])


class InitializeAuthDB(LazyFunction):
    def __call__(self):
        cli = pymongo.mongo_client.MongoClient(
            f"mongodb://root:rootPass@{common.HOST}:{common.PORT1}",
            socketTimeoutMS=30000,
            read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,
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

        for db_name in ['admin']:
            db = cli[db_name]
            db.foo.insert_many(foos)
            db.bar.insert_many(bars)
            db.orders.insert_many(orders)
            db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': db_name}])

        auth_db = cli['authDB']
        auth_db.command(
            "createUser",
            'testUser',
            pwd='testPass',
            roles=[
                {'role': 'read', 'db': 'test'},
                {'role': "clusterManager", 'db': "admin"},
                {'role': "clusterMonitor", 'db': "admin"},
            ],
        )
        auth_db.command("createUser", 'special test user', pwd='s3\\kr@t', roles=[{'role': 'read', 'db': 'test'}])
