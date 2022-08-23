# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pymongo
import pytest

from datadog_checks.dev import LazyFunction, docker_run
from datadog_checks.dev.conditions import WaitForPortListening

from . import common


class InitializeDB(LazyFunction):
    def __call__(self):
        cli = pymongo.mongo_client.MongoClient(
            "mongodb://%s:%s" % (common.HOST, common.PORT),
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


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'compose', common.COMPOSE_FILE)
    conditions = [
        WaitForPortListening(common.HOST, common.PORT),
        InitializeDB(),
    ]
    with docker_run(
        compose_file,
        conditions=conditions,
    ):
        yield common.INSTANCE_BASIC, {}


@pytest.fixture
def instance():
    return {}
