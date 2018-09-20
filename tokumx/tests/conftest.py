# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os
import pymongo

from datadog_checks.dev import docker_run
from datadog_checks.tokumx import TokuMX

from . import common


@pytest.fixture(scope="session")
def spin_up_tokumx(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    compose_dir = os.path.join(common.HERE, 'compose')
    env = {
        'COMPOSE_DIR': compose_dir
    }

    with docker_run(compose_file,
                    log_patterns='admin web console waiting for connections',
                    env_vars=env):
        yield


@pytest.fixture
def check():
    return TokuMX('tokumx', {}, {})


@pytest.fixture(scope="session")
def set_up_tokumx():
    cli = pymongo.mongo_client.MongoClient(
        common.TOKUMX_SERVER,
        socketTimeoutMS=30000,
        read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,)

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

    # authDB = cli['authDB']
    # authDB.command("createUser", 'testUser', pwd='testPass', roles=[{'role': 'read', 'db': 'test'}])
    #
    # db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': 'test'}])

    yield
    tear_down_tokumx()


def tear_down_tokumx():
    cli = pymongo.mongo_client.MongoClient(
        common.TOKUMX_SERVER,
        socketTimeoutMS=30000,
        read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,)

    db = cli['test']
    db.drop_collection("foo")
    db.drop_collection("bar")
