# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.riak import Riak

from . import common


def populate():
    res = requests.post(
        "{}/riak/bucket/german".format(common.BASE_URL),
        headers={"Content-Type": "text/plain"},
        data='herzlich willkommen',
    )
    res.raise_for_status

    res = requests.get("{}/riak/bucket/german".format(common.BASE_URL))
    res.raise_for_status


@pytest.fixture(scope="session")
def dd_environment():
    env = {'RIAK_CONFIG': os.path.join(common.HERE, 'config')}
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'riak.yaml'),
        env_vars=env,
        conditions=[CheckEndpoints(['{}/riak/bucket'.format(common.BASE_URL)]), populate],
        sleep=10,  # some stats require a bit of time before the test will capture them
    ):
        yield common.INSTANCE


@pytest.fixture
def check():
    return Riak('riak', {}, [deepcopy(common.INSTANCE)])


@pytest.fixture
def instance():
    instance = deepcopy(common.INSTANCE)
    return instance
