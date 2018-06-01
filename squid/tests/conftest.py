# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import subprocess
import time

import pytest
import requests

from datadog_checks.squid import SquidCheck
from . import common


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def squid_check():
    return SquidCheck(common.CHECK_NAME, {}, {})


@pytest.fixture(scope="session")
def spin_up_squid():
    env = os.environ
    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'squid.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)
    for _ in xrange(10):
        try:
            res = requests.get(common.URL)
            res.raise_for_status()
            break
        except Exception:
            time.sleep(1)
            sys.stderr.write("Waiting for Squid to boot...")
    else:
        subprocess.check_call(args + ["down"], env=env)
        raise Exception("Squid failed to boot...")

    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def instance():
    instance = {
        "name": "ok_instance",
        "tags": ["custom_tag"],
        "host": common.HOST
    }
    return instance
