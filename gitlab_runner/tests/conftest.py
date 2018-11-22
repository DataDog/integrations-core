# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from .common import (
    HERE, GITLAB_TEST_TOKEN, GITLAB_RUNNER_URL, GITLAB_LOCAL_RUNNER_PORT, GITLAB_LOCAL_MASTER_PORT
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session", autouse=True)
def gitlab_runner_service(request):
    """
    Spin up and initialize gitlab_runner
    """

    # specify couchbase container name
    env = os.environ
    env['GITLAB_TEST_TOKEN'] = GITLAB_TEST_TOKEN
    env['GITLAB_LOCAL_MASTER_PORT'] = str(GITLAB_LOCAL_MASTER_PORT)
    env['GITLAB_LOCAL_RUNNER_PORT'] = str(GITLAB_LOCAL_RUNNER_PORT)

    args = [
        'docker-compose',
        '-f', os.path.join(HERE, 'compose', 'docker-compose.yml')
    ]

    # always stop and remove the container even if there's an exception at setup
    def teardown():
        subprocess.check_call(args + ["down"], env=env)
    request.addfinalizer(teardown)

    # spin up the docker container
    subprocess.check_call(args + ['up', '-d'], env=env)

    # wait for gitlab_runner to be up, it depends on gitlab
    if not wait_for(GITLAB_RUNNER_URL):
        raise Exception("gitlab_runner container timed out!")

    # run pre-test commands
    for i in xrange(100):
        requests.get(GITLAB_RUNNER_URL)
    sleep(2)

    yield


def wait_for(URL):
    """
    Wait for specified URL
    """

    for i in xrange(180):
        try:
            r = requests.get(URL)
            r.raise_for_status()
            return True
        except Exception:
            pass

        sleep(1)

    return False
