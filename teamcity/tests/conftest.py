# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2, PY3

from datadog_checks.dev import docker_run
from datadog_checks.teamcity.teamcity_rest import TeamCityRest

if PY3:
    from datadog_checks.teamcity.teamcity_openmetrics import TeamCityOpenMetrics

from .common import COMPOSE_FILE, LEGACY_REST_INSTANCE, OPENMETRICS_INSTANCE, REST_INSTANCE, USE_OPENMETRICS


@pytest.fixture(scope='session')
def dd_environment(instance, openmetrics_instance):
    with docker_run(COMPOSE_FILE, sleep=10):
        if USE_OPENMETRICS:
            yield openmetrics_instance
        else:
            yield instance


@pytest.fixture(scope='session')
def rest_instance():
    if PY2:
        return LEGACY_REST_INSTANCE
    else:
        return REST_INSTANCE


@pytest.fixture(scope='session')
def openmetrics_instance():
    return OPENMETRICS_INSTANCE


@pytest.fixture(scope="session")
def teamcity_rest_check():
    return lambda instance: TeamCityRest('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def teamcity_om_check():
    return lambda instance: TeamCityOpenMetrics('teamcity', {}, [instance])
