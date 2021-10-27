# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.utils import load_jmx_config

@pytest.fixture(scope='session')
def dd_environment():
    properties_dir = os.path.join(get_here(), 'compose', 'properties')
    compose_file = os.path.join(get_here(), 'compose', 'docker-compose.yml')
    with docker_run(
        compose_file,
        env_vars={'PROPERTIES_DIR': properties_dir}
    ):
        yield load_jmx_config(), {'use_jmx': True}
