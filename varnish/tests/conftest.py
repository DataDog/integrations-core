# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.varnish import Varnish

from . import common

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}


@pytest.fixture
def check():
    return Varnish(common.CHECK_NAME, {}, {})


@pytest.fixture(scope='session')
def dd_environment():
    varnish_version = os.getenv("VARNISH_VERSION")
    if varnish_version.startswith("5"):
        compose_file = os.path.join(common.HERE, 'compose', 'docker-compose-4-5.yaml')
    else:
        compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    with docker_run(compose_file, log_patterns=[r'Child \(\d+\) Started', r'Child \(\d+\) said Child starts'], sleep=2):
        yield common.get_config_by_version(), E2E_METADATA


@pytest.fixture
def instance():
    return common.get_config_by_version()
