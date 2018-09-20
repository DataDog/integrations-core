# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from .common import (
    HERE, GITLAB_URL, PROMETHEUS_ENDPOINT, GITLAB_TEST_PASSWORD, GITLAB_LOCAL_PORT, GITLAB_LOCAL_PROMETHEUS_PORT
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session", autouse=True)
def gitlab_service(request):
    """
    Spin up and initialize gitlab
    """

    # specify couchbase container name
    env = os.environ
    env['GITLAB_TEST_PASSWORD'] = GITLAB_TEST_PASSWORD
    env['GITLAB_LOCAL_PORT'] = str(GITLAB_LOCAL_PORT)
    env['GITLAB_LOCAL_PROMETHEUS_PORT'] = str(GITLAB_LOCAL_PROMETHEUS_PORT)

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

    # wait for gitlab to be up
    if not wait_for(GITLAB_URL, timeout=200):
        raise Exception("gitlab container timed out!")

    # wait for prometheus endpoint to be up
    if not wait_for(PROMETHEUS_ENDPOINT, timeout=20):
        raise Exception("prometheus endpoint timed out!")

    # run pre-test commands
    for i in xrange(100):
        requests.get(GITLAB_URL)
    sleep(2)

    yield


def wait_for(URL, timeout):
    """
    Wait for specified URL
    """

    for i in xrange(timeout):
        try:
            r = requests.get(URL)
            r.raise_for_status()
            return True
        except Exception:
            pass

        sleep(1)

    return False
