# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pytest
import requests
from mock import MagicMock, patch

from datadog_checks.dev import LazyFunction, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.harbor import HarborCheck
from datadog_checks.harbor.api import HarborAPI
from datadog_checks.harbor.common import (
    CHARTREPO_HEALTH_URL,
    HEALTH_URL,
    LOGIN_PRE_1_7_URL,
    LOGIN_URL,
    PING_URL,
    PROJECTS_URL,
    REGISTRIES_PING_PRE_1_8_URL,
    REGISTRIES_PING_URL,
    REGISTRIES_PRE_1_8_URL,
    REGISTRIES_URL,
    SYSTEM_INFO_URL,
    VOLUME_INFO_URL,
)

from .common import (
    ADMIN_INSTANCE,
    CHARTREPO_HEALTH_FIXTURE,
    HARBOR_VERSION,
    HEALTH_FIXTURE,
    HERE,
    INSTANCE,
    PROJECTS_FIXTURE,
    REGISTRIES_FIXTURE,
    REGISTRIES_PRE_1_8_FIXTURE,
    SYSTEM_INFO_FIXTURE,
    URL,
    USERS_URL,
    VERSION_1_6,
    VERSION_1_8,
    VOLUME_INFO_FIXTURE,
)

UNTRACKED_FILES = [
    os.path.join('common', 'config', 'core', 'certificates'),
    os.path.join('common', 'config', 'custom-ca-bundle.crt'),
    os.path.join('common', 'config', 'ui', 'certificates'),
    os.path.join('data', 'ca_download'),
    os.path.join('data', 'chart_storage'),
    os.path.join('data', 'config'),
    os.path.join('data', 'job_logs'),
    os.path.join('data', 'psc'),
    os.path.join('data', 'redis'),
    os.path.join('data', 'registry'),
]


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
    return check


@pytest.fixture
def harbor_api(harbor_check, admin_instance, patch_requests):
    yield HarborAPI(URL, harbor_check.http)


@pytest.fixture
def patch_requests():
    with patch.object(requests.Session, 'request', side_effect=mocked_requests):
        yield


def get_docker_compose_file():
    harbor_version = os.environ['HARBOR_VERSION']
    harbor_folder = 'harbor-{}'.format(harbor_version)
    return os.path.join(HERE, 'compose', harbor_folder, 'docker-compose.yml')


class MockResponse:
    def __init__(self, json_or_text, status_code):
        self.json_or_text = json_or_text
        self.status_code = status_code
        self.text = json_or_text
        self.content = json_or_text
        self.json = lambda: self.json_or_text
        self.links = []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("[MockedResponse] Status code is {}".format(self.status_code))


def mocked_requests(_, *args, **kwargs):
    def match(url, *candidates_url):
        for c in candidates_url:
            if url == c.format(base_url=URL):
                return True
        return False

    if match(args[0], LOGIN_PRE_1_7_URL, LOGIN_URL):
        return MockResponse(None, 200)
    elif match(args[0], HEALTH_URL) and HARBOR_VERSION >= VERSION_1_8:
        return MockResponse(HEALTH_FIXTURE, 200)
    elif match(args[0], PING_URL):
        return MockResponse("Pong", 200)
    elif match(args[0], CHARTREPO_HEALTH_URL) and HARBOR_VERSION >= VERSION_1_6:
        return MockResponse(CHARTREPO_HEALTH_FIXTURE, 200)
    elif match(args[0], PROJECTS_URL):
        return MockResponse(PROJECTS_FIXTURE, 200)
    elif match(args[0], REGISTRIES_PRE_1_8_URL, REGISTRIES_URL):
        if HARBOR_VERSION >= VERSION_1_8:
            return MockResponse(REGISTRIES_FIXTURE, 200)
        return MockResponse(REGISTRIES_PRE_1_8_FIXTURE, 200)
    elif match(args[0], REGISTRIES_PING_PRE_1_8_URL, REGISTRIES_PING_URL):
        return MockResponse(None, 200)
    elif match(args[0], VOLUME_INFO_URL):
        return MockResponse(VOLUME_INFO_FIXTURE, 200)
    elif match(args[0], SYSTEM_INFO_URL):
        return MockResponse(SYSTEM_INFO_FIXTURE, 200)

    return MockResponse(None, 404)
