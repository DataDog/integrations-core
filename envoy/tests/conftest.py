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
    # Drive continuous traffic through Envoy's listener for one full stats
    # flush interval so the most recent flush window always has samples.
    # Envoy's text /stats endpoint reports per-interval quantile values
    # that get recomputed on every flush; an empty flush resets the
    # interval percentiles to nan (see hist_approx_quantile in
    # libcircllhist), which the parser would then filter out. Spreading
    # requests across the window keeps the interval quantiles populated
    # regardless of where the test lands in Envoy's flush cycle.
    #
    # Budget note: this buys us roughly one full flush interval of safe
    # scrape window after the fixture yields, before the next empty flush
    # wipes the interval values. The agent's --check-rate scrape typically
    # takes 3-7s, so it lands comfortably inside that window. If the agent
    # invocation ever gets significantly slower (e.g. longer rate delays
    # or extra setup work) raise stats_flush_interval in front-envoy.yaml
    # instead of leaning on this buffer.
    deadline = time.monotonic() + ENVOY_STATS_FLUSH_INTERVAL + 1
    while time.monotonic() < deadline:
        requests.get('http://{}:8000/service/1'.format(HOST))
        requests.get('http://{}:8000/service/2'.format(HOST))
        time.sleep(ENVOY_STATS_FLUSH_INTERVAL / 10)


@pytest.fixture
def check():
    return lambda instance: Envoy('envoy', {}, [instance])


@pytest.fixture
def default_instance():
    return copy.deepcopy(DEFAULT_INSTANCE)
