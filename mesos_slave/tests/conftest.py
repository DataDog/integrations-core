# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.mesos_slave import MesosSlave

from . import common


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
    return MesosSlave(common.CHECK_NAME, {}, {})


@pytest.fixture
def check_mock(check):
    check._get_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_state = lambda v, x: json.loads(read_fixture('state.json'))

    return check


def read_fixture(name):
    with open(os.path.join(common.FIXTURE_DIR, name)) as f:
        return f.read()
