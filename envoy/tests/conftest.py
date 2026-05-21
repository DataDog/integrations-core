# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, DOCKER_DIR, FIXTURE_DIR, HOST, URL
from .legacy.common import FLAVOR, INSTANCES


@pytest.fixture(scope='session')
def fixture_path():
    yield lambda name: os.path.join(FIXTURE_DIR, name)


@pytest.fixture(scope='session')
def dd_environment():
    if FLAVOR == 'api_v2':
        instance = INSTANCES['main']
    else:
        instance = DEFAULT_INSTANCE

    with docker_run(
        os.path.join(DOCKER_DIR, FLAVOR, 'docker-compose.yaml'),
        build=True,
        endpoints="{}/stats".format(URL),
        log_patterns=['front-envoy(.*?)all dependencies initialized. starting workers'],
        sleep=10,
        attempts=5,
        attempts_wait=10,
    ):
        yield instance


@pytest.fixture
def exercise_envoy():
    # Fire requests through Envoy's listener and wait long enough for at
    # least one stats flush to roll the samples into the histogram interval
    # view. Envoy's text /stats endpoint reports per-interval quantile values
    # that update on each 5s flush; the parser drops any percentile whose
    # interval value is nan. Without the sleep the scrape can land before
    # the first flush after the requests (interval=nan, no metric emitted)
    # or after multiple empty flushes have wiped the values (also nan).
    # 6 seconds reliably lands us in the "one flush has captured the
    # requests, next empty flush hasn't reset yet" window.
    requests.get('http://{}:8000/service/1'.format(HOST))
    requests.get('http://{}:8000/service/2'.format(HOST))
    time.sleep(6)


@pytest.fixture
def check():
    return lambda instance: Envoy('envoy', {}, [instance])


@pytest.fixture
def default_instance():
    return copy.deepcopy(DEFAULT_INSTANCE)
