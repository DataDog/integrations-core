# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import threading
import time

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, DOCKER_DIR, FIXTURE_DIR, HOST, URL
from .legacy.common import FLAVOR, INSTANCES

# Envoy's default stats_flush_interval (seconds). The exercise_envoy
# fixture drives traffic for one full interval so the most recent
# completed flush window always has samples; if Envoy's default changes
# (or we ever set the interval explicitly in the test bootstrap config),
# update this constant and the fixture timings follow.
ENVOY_STATS_FLUSH_INTERVAL = 5


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
    # Drive continuous traffic through Envoy's listener for the entire
    # lifetime of the test. A background thread keeps firing requests
    # until the fixture tears down, so every flush window — including
    # those that close while the agent's check is in flight — has
    # samples. Envoy's text /stats endpoint reports per-interval
    # quantile values that get recomputed on every flush; an empty
    # flush resets the interval percentiles to nan (see
    # hist_approx_quantile in libcircllhist), which the parser would
    # then filter out.
    stop = threading.Event()

    def fire_loop():
        while not stop.is_set():
            try:
                requests.get('http://{}:8000/service/1'.format(HOST))
                requests.get('http://{}:8000/service/2'.format(HOST))
            except requests.RequestException:
                pass
            stop.wait(ENVOY_STATS_FLUSH_INTERVAL / 10)

    thread = threading.Thread(target=fire_loop, daemon=True)
    thread.start()
    # Wait one full flush interval so the first non-empty flush rolls
    # samples into the interval percentile view before the test body
    # starts scraping.
    time.sleep(ENVOY_STATS_FLUSH_INTERVAL + 1)
    yield
    stop.set()
    thread.join(timeout=2)


@pytest.fixture
def check():
    return lambda instance: Envoy('envoy', {}, [instance])


@pytest.fixture
def default_instance():
    return copy.deepcopy(DEFAULT_INSTANCE)
