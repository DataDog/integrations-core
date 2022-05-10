# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.tokumx import TokuMX
from datadog_checks.tokumx.vendor import pymongo

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing `docker compose`, let the exception bubble
    up.
    """
    compose_dir = os.path.join(common.HERE, 'compose')
    with docker_run(
        compose_file=os.path.join(compose_dir, 'docker-compose.yaml'),
        log_patterns='admin web console waiting for connections',
        env_vars={'COMPOSE_DIR': compose_dir},
    ):
        set_up_tokumx()
        yield common.INSTANCE


@pytest.fixture
def check():
    return TokuMX('tokumx', {}, {})


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


def set_up_tokumx():
    cli = pymongo.MongoClient(
        common.TOKUMX_SERVER, socketTimeoutMS=30000, read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED
    )

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
