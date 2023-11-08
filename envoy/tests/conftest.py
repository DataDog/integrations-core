# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

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
        attempts=2,
    ):
        # Exercising envoy a bit will trigger extra metrics
        requests.get('http://{}:8000/service/1'.format(HOST))
        requests.get('http://{}:8000/service/2'.format(HOST))
        yield instance


@pytest.fixture
def check():
    return lambda instance: Envoy('envoy', {}, [instance])


@pytest.fixture
def default_instance():
    return copy.deepcopy(DEFAULT_INSTANCE)
