# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time
import pytest
import requests

from copy import deepcopy

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.squid import SquidCheck

from . import common


def wait_for_squid():
    try:
        res = requests.get(common.URL)
        res.raise_for_status()
        return True
    except Exception:
        time.sleep(1)
        sys.stderr.write("Waiting for Squid to boot...")
        return False


@pytest.fixture(scope='session')
def dd_environment():
    env = os.environ
    with docker_run(
            compose_file=os.path.join(common.HERE, 'compose', 'squid.yaml'),
            env_vars=env,
            conditions=[WaitFor(wait_for_squid)],
    ):
        yield common.CHECK_CONFIG


@pytest.fixture
def check():
    return SquidCheck(common.CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(common.CHECK_CONFIG)
    return instance
