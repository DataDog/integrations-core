# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY3

from datadog_checks.dev import docker_run
from datadog_checks.teamcity import TeamCityCheck

if PY3:
    from datadog_checks.teamcity.check import TeamCityCheckV2

from .common import COMPOSE_FILE, CONFIG


@pytest.fixture(scope='session')
def dd_environment(instance, omv2_instance):
    with docker_run(COMPOSE_FILE, sleep=10):
        yield [instance, omv2_instance]


@pytest.fixture(scope='session')
def legacy_instance():
    return CONFIG['instances'][0]


@pytest.fixture(scope='session')
def instance():
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
