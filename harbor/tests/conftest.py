# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import mock
import pytest
import requests

from datadog_checks.dev import LazyFunction, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.harbor import HarborAPI, HarborCheck

from .common import ADMIN_INSTANCE, HARBOR_VERSION, HERE, INSTANCE, URL, USERS_URL, MockedHarborAPI


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = get_docker_compose_file()
    conditions = [
        CheckDockerLogs(compose_file, "http server Running on", wait=3),
        lambda: time.sleep(2),
        CreateSimpleUser(),
    ]

    with docker_run(compose_file, conditions=conditions):
        yield instance


class CreateSimpleUser(LazyFunction):
    def __call__(self, *args, **kwargs):
        with requests.session() as session:
            harbor_api = HarborAPI(URL, session)
            harbor_api.authenticate('admin', 'Harbor12345')
            harbor_api._make_post_request(
                USERS_URL,
                json={
                    "username": "NotAnAdmin",
                    "email": "NotAnAdmin@goharbor.io",
                    "password": "Str0ngPassw0rd",
                    "realname": "Not An Admin",
                },
            )


@pytest.fixture(scope='session')
def instance():
    return INSTANCE.copy()


@pytest.fixture(scope='session')
def admin_instance():
    return ADMIN_INSTANCE.copy()


@pytest.fixture
def harbor_check(admin_instance):
    check = HarborCheck('harbor', {}, [admin_instance])
    check.log = mock.MagicMock()
    check.gauge = mock.MagicMock()
    check.count = mock.MagicMock()
    check.service_check = mock.MagicMock()
    return check


@pytest.fixture
def harbor_api():
    with mock.patch('datadog_checks.harbor.harbor.HarborAPI', new=MockedHarborAPI) as api:
        yield api


def get_docker_compose_file():
    harbor_version = HARBOR_VERSION
    harbor_folder = 'harbor-{}'.format(harbor_version)
    return os.path.join(HERE, 'compose', harbor_folder, 'docker-compose.yml')
