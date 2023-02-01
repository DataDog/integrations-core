# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from packaging.version import parse as parse_version

from datadog_checks.dev import docker_run

from .common import COCKROACHDB_VERSION, HOST, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture(scope='session')
def dd_environment(instance):
    env_vars = {'COCKROACHDB_START_COMMAND': _get_start_command()}
    with docker_run(
        os.path.join(DOCKER_DIR, 'docker-compose.yaml'),
        env_vars=env_vars,
        endpoints=instance['openmetrics_endpoint'],
    ):
        yield instance


@pytest.fixture(scope='session')
def instance_legacy():
    return {'prometheus_url': 'http://{}:{}/_status/vars'.format(HOST, PORT)}


@pytest.fixture(scope='session')
def instance():
    return {'openmetrics_endpoint': 'http://{}:{}/_status/vars'.format(HOST, PORT)}


def _get_start_command():
    if COCKROACHDB_VERSION != 'latest' and parse_version(COCKROACHDB_VERSION) < parse_version('20.2'):
        return 'start'
    return 'start-single-node'
