# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from common import (
    HERE, URL
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def kyototycoon():
    """
    Spin up a kyototycoon docker image
    """
    args = [
        'docker-compose',
        '-f', os.path.join(HERE, 'compose', 'compose_kyototycoon.yaml')
    ]

    subprocess.check_call(args + ["up", "-d"])

    # wait for kyototycoon to be up
    if not wait_for_kyototycoon():
        raise Exception("kyototycoon container boot timed out!")

    # Generate a test database
    data = {
        'dddd': 'dddd'
    }
    headers = {
        'X-Kt-Mode': 'set'
    }

    for i in xrange(100):
        requests.put(URL, data=data, headers=headers)
        requests.get(URL)

    yield

    subprocess.check_call(args + ["down"])


def wait_for_kyototycoon():
    """
    Wait for the kyototycoon container to be reachable
    """
    for i in xrange(40):
        sleep(1)
        try:
            requests.get('{0}/rpc/report'.format(URL)).raise_for_status()
            return True
        except Exception:
            pass

    return False
