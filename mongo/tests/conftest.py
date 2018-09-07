# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import logging
import time

import pymongo
import pytest

from datadog_checks.mongo import MongoDb

from . import common

log = logging.getLogger('conftest')


@pytest.fixture
def check():
    check = MongoDb('mongo', {}, {})
    return check


@pytest.fixture(scope="session")
def set_up_mongo():
    cli = pymongo.mongo_client.MongoClient(
        common.MONGODB_SERVER,
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

    authDB = cli['authDB']
    authDB.command("createUser", 'testUser', pwd='testPass', roles=[{'role': 'read', 'db': 'test'}])

    db.command("createUser", 'testUser2', pwd='testPass2', roles=[{'role': 'read', 'db': 'test'}])

    yield
    tear_down_mongo()


def tear_down_mongo():
    cli = pymongo.mongo_client.MongoClient(
        common.MONGODB_SERVER,
        socketTimeoutMS=30000,
        read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,)

    db = cli['test']
    db.drop_collection("foo")
    db.drop_collection("bar")


@pytest.fixture(scope="session")
def spin_up_mongo():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = os.environ

    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yml')

    env['DOCKER_COMPOSE_FILE'] = compose_file

    args = [
        "docker-compose",
        "-f", compose_file
    ]

    try:
        subprocess.check_call(args + ["up", "-d"], env=env)
        setup_sharding(env=env)
    except Exception:
        cleanup_mongo(args, env)
        raise

    yield
    cleanup_mongo(args, env)


def setup_sharding(env=None):
    curdir = os.getcwd()
    compose_dir = os.path.join(common.HERE, 'compose')
    os.chdir(compose_dir)
    for i in xrange(5):
        try:
            subprocess.check_call(['bash', 'init.sh'], env=env)
            os.chdir(curdir)
            return
        except Exception as e:
            log.info(e)
            time.sleep(5)

    os.chdir(curdir)
    raise e


def cleanup_mongo(args, env):
    subprocess.check_call(args + ["down"], env=env)
    # it creates a lot of volumes, this is necessary
    try:
        subprocess.check_call(['docker', 'volume', 'prune', '-f'])
    except Exception:
        pass
