# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os
import requests
import time
import logging

from copy import deepcopy
from datadog_checks.riak import Riak
from datadog_checks.dev import WaitFor, docker_run

from . import common


log = logging.getLogger('test_riak')


def wait_for_riak():
    can_access = False
    for _ in range(0, 10):
        res = None
        try:
            res = requests.get("{0}/riak/bucket".format(common.BASE_URL))
            log.info("response: {0}".format(res))
            log.info("status code: {0}, text: {1}".format(res.status_code, res.text))
            res.raise_for_status
            can_access = True
            break
        except Exception as e:
            log.info("exception: {0}, response: {1}".format(e, res))
            time.sleep(5)
    if not can_access:
        raise Exception("Cannot access Riak")

    data = 'herzlich willkommen'
    headers = {"Content-Type": "text/plain"}
    for _ in range(0, 10):
        res = requests.post(
            "{0}/riak/bucket/german".format(common.BASE_URL),
            headers=headers,
            data=data)
        res.raise_for_status
        res = requests.get("{0}/riak/bucket/german".format(common.BASE_URL))
        res.raise_for_status


@pytest.fixture(scope="session")
def dd_environment():
    env = os.environ
    env['RIAK_CONFIG'] = os.path.join(common.HERE, 'config')

    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'riak.yaml'),
        env_vars=env,
        conditions=[WaitFor(wait_for_riak)],
        sleep=10,  # some stats require a bit of time before the test will capture them
    ):
        yield common.INSTANCE


@pytest.fixture
def check():
    return Riak('riak', {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(common.INSTANCE)
    return instance
