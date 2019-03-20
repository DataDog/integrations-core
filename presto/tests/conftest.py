# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import pytest

from datadog_checks.dev.utils import load_jmx_config
from datadog_checks.dev import docker_run, get_here


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(os.path.join(get_here(), 'docker', 'docker-compose.yaml')):
        yield instance


@pytest.fixture(scope='session', autouse=True)
@pytest.mark.usefixtures('dd_environment')
def instance():
    return load_jmx_config()
