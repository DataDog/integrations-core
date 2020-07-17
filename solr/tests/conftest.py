# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.utils import load_jmx_config

from .common import HOST


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(os.path.join(get_here(), 'docker', 'docker-compose.yml')):
        instance = load_jmx_config()
        instance['instances'][0]['host'] = HOST
        instance['instances'][0]['port'] = 18983
        instance['instances'].append(copy.deepcopy(instance['instances'][0]))
        instance['instances'][1]['host'] = HOST
        instance['instances'][1]['port'] = 18982
        instance['instances'].append(copy.deepcopy(instance['instances'][0]))
        instance['instances'][2]['host'] = HOST
        instance['instances'][2]['port'] = 18981
        yield instance, {'use_jmx': True}
