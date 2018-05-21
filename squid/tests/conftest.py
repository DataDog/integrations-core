# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
import os
import subprocess
import requests
import time
import logging
import common

log = logging.getLogger('test_squid')


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def spin_up_squid():
    env = os.environ
    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'squid.yaml')
    ]

    subprocess.check_call(args + ["down"], env=env)
    subprocess.check_call(args + ["up", "-d"], env=env)

    for _ in xrange(30):
        try:
            res = requests.get(common.URL)
            res.raise_for_status()
            break
        except Exception:
            time.sleep(1)
    yield
    subprocess.check_call(args + ["down"], env=env)
