# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.mesos_slave import MesosSlave

from . import common
from .utils import read_fixture


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yml')

    with docker_run(compose_file, service_name='mesos-slave', log_patterns=['Finished recovery']):
        yield common.INSTANCE


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture
def check():
    return mock


def mock(init_config, instance):
    check = MesosSlave(common.CHECK_NAME, init_config, [instance])

    check._get_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_state = lambda v, x: json.loads(read_fixture('state.json'))

    return check
