# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.mesos_master import MesosMaster

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yml')

    with docker_run(compose_file, service_name="mesos-master", log_patterns=['A new leading master']):
        yield instance


@pytest.fixture
def check():
    return MesosMaster(common.CHECK_NAME, {}, [common.INSTANCE])


@pytest.fixture(scope='session')
def instance():
    return common.INSTANCE
