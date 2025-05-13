# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE

HERE = os.path.join(HERE, 'compose')


@pytest.fixture(scope='session')
def dd_environment(instance):
    properties_dir = os.path.join(HERE, 'weblogic', 'properties')
    compose_file = os.path.join(HERE, 'docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        env_vars={'PROPERTIES_DIR': properties_dir},
        sleep=60,
        build=True,
        attempts=2,
    ):
        yield instance, {'use_jmx': True}


@pytest.fixture(scope='session', autouse=True)
@pytest.mark.usefixtures('dd_environment')
def instance():
    inst = load_jmx_config()
    # Add managed servers to the configuration
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9091
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9092

    return inst
