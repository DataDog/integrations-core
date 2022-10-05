# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY3

from datadog_checks.dev import docker_run
from datadog_checks.teamcity import TeamCityCheck

if PY3:
    from datadog_checks.teamcity.check import TeamCityCheckV2

from .common import COMPOSE_FILE, LEGACY_INSTANCE, TEAMCITY_OMV2_INSTANCE, TEAMCITY_V2_INSTANCE, USE_OPENMETRICS


@pytest.fixture(scope='session')
def dd_environment(instance, omv2_instance):
    with docker_run(COMPOSE_FILE, sleep=10):
        if USE_OPENMETRICS:
            yield omv2_instance
        else:
            yield instance


@pytest.fixture(scope='session')
def legacy_instance():
    return LEGACY_INSTANCE


@pytest.fixture(scope='session')
def instance():
    return TEAMCITY_V2_INSTANCE


@pytest.fixture(scope='session')
def omv2_instance():
    return TEAMCITY_OMV2_INSTANCE


@pytest.fixture(scope="session")
def check():
    return lambda instance: TeamCityCheck('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def check_v2():
    return lambda instance: TeamCityCheckV2('teamcity', {}, [instance])
