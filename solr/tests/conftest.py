# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.utils import load_jmx_config


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(os.path.join(get_here(), 'docker', 'docker-compose.yml')):
        instance = load_jmx_config()
        instance['instances'][0]['port'] = 18983
        yield instance, {'use_jmx': True}
