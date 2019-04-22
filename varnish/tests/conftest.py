# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.varnish import Varnish

from . import common


@pytest.fixture
def check():
    return Varnish(common.CHECK_NAME, {}, {})


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    with docker_run(compose_file, sleep=2):
        yield common.get_config_by_version(), 'local'


@pytest.fixture
def instance():
    return common.get_config_by_version()
