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
def dd_environment():
    with docker_run(COMPOSE_FILE, sleep=10):
        if USE_OPENMETRICS:
            yield omv2_instance
        else:
            yield instance


@pytest.fixture()
def instance():
    return CONFIG['instances'][0]


@pytest.fixture()
def omv2_instance():
    return CONFIG['instances'][1]


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


@pytest.fixture()
def mock_prometheus_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
