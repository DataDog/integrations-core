# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pymongo
import pytest

from datadog_checks.dev import LazyFunction, WaitFor, docker_run, run_command
from datadog_checks.mongo import MongoDb
from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yml')

    with docker_run(
        compose_file,
        conditions=[
            WaitFor(setup_sharding, args=(compose_file, ), attempts=5, wait=5),
            InitializeDB(),
        ],
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'server': common.MONGODB_SERVER,
    }


@pytest.fixture
def instance_user():
    return {
        'server': 'mongodb://testUser2:testPass2@{}:{}/test'.format(common.HOST, common.PORT1),
    }


@pytest.fixture
def instance_authdb():
    return {
        'server': 'mongodb://testUser:testPass@{}:{}/test?authSource=authDB'.format(common.HOST, common.PORT1),
    }


@pytest.fixture
def check():
    return MongoDb('mongo', {}, {})


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
            common.MONGODB_SERVER,
            socketTimeoutMS=30000,
            read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED, )

        foos = []
        for _ in range(70):
            foos.append({'1': []})
            foos.append({'1': []})
            foos.append({})

        bars = []
        for _ in range(50):
            bars.append({'1': []})
            bars.append({})

        db = cli['test']
        db.foo.insert_many(foos)
        db.bar.insert_many(bars)

        auth_db = cli['authDB']
        auth_db.command("createUser", 'testUser', pwd='testPass', roles=[{'role': 'read', 'db': 'test'}])

        db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': 'test'}])
