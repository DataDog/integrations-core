# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY3

from datadog_checks.dev import docker_run
from datadog_checks.teamcity import TeamCityCheck

if PY3:
    from datadog_checks.teamcity.check import TeamCityCheckV2

from .common import COMPOSE_FILE, INSTANCE, LEGACY_INSTANCE, OPENMETRICS_INSTANCE, USE_OPENMETRICS


@pytest.fixture(scope='session')
def dd_environment(instance, openmetrics_instance):
    with docker_run(COMPOSE_FILE, sleep=10):
        if USE_OPENMETRICS:
            yield openmetrics_instance
        else:
            yield instance


@pytest.fixture(scope='session')
def legacy_instance():
    return LEGACY_INSTANCE


@pytest.fixture(scope='session')
def instance():
    return INSTANCE


@pytest.fixture(scope='session')
def openmetrics_instance():
    return OPENMETRICS_INSTANCE


@pytest.fixture(scope="session")
def teamcity_check():
    return lambda instance: TeamCityCheck('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def teamcity_check_v2():
    return lambda instance: TeamCityCheckV2('teamcity', {}, [instance])
