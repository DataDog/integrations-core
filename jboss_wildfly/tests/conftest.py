# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(os.path.join(HERE, 'docker', 'docker-compose.yml')):
        yield load_jmx_config(), 'local'
