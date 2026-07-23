# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import http.client
import os
from copy import deepcopy
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.riak import Riak

from . import common


def response_ok(http_request: Request) -> bool:
    try:
        with urlopen(http_request) as response:
            return response.status < http.client.BAD_REQUEST
    except HTTPError as e:
        e.close()
        return e.code < http.client.BAD_REQUEST


def populate():
    post = response_ok(
        Request(
            "{}/riak/bucket/german".format(common.BASE_URL),
            data=b'herzlich willkommen',
            headers={"Content-Type": "text/plain"},
            method='POST',
        )
    )
    get = response_ok(
        Request(
            "{}/riak/bucket/german".format(common.BASE_URL),
            method='GET',
        )
    )
    return post and get


@pytest.fixture(scope="session")
def dd_environment():
    env = {'RIAK_CONFIG': os.path.join(common.HERE, 'config')}
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'riak.yaml'),
        env_vars=env,
        conditions=[CheckEndpoints(['{}/riak/bucket'.format(common.BASE_URL)]), WaitFor(populate)],
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
