# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE, HOST, JMX_PORT


@pytest.fixture(scope="session")
def dd_environment():
    env_vars = {'JMX_HOST': HOST, 'JMX_PORT': JMX_PORT}
    with docker_run(os.path.join(HERE, 'docker', 'docker-compose.yml', env_vars=env_vars)):
        yield load_jmx_config(), 'local'
