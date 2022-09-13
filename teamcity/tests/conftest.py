# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.teamcity import TeamCityCheck
from datadog_checks.teamcity.check import TeamCityCheckV2

from .common import COMPOSE_FILE, CONFIG, SERVER_URL

USE_OPENMETRICS = os.getenv('USE_OPENMETRICS')


@pytest.fixture(scope='session')
def dd_environment(instance, omv2_instance):
    with docker_run(COMPOSE_FILE, sleep=10):
        if USE_OPENMETRICS:
            yield omv2_instance
        else:
            yield instance


@pytest.fixture(scope='session')
def legacy_instance():
    return CONFIG['instances'][0]


@pytest.fixture(scope='session')
def tcv2_instance():
    return CONFIG['instances'][1]


@pytest.fixture(scope='session')
def omv2_instance():
    return CONFIG['instances'][2]


@pytest.fixture(scope="session")
def check():
    return lambda instance: TeamCityCheck('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def check_v2():
    return lambda instance: TeamCityCheckV2('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def omv2_instance_use_openmetrics():
    return lambda use_openmetrics: {
        'server': SERVER_URL,
        'tags': ['teamcity:test'],
        'use_openmetrics': use_openmetrics,
    }
