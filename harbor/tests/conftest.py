# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pytest
import requests
from mock import patch

from datadog_checks.dev import LazyFunction, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.http import MockResponse
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
    VERSION_2_2,
    VOLUME_INFO_FIXTURE,
    VOLUME_INFO_PRE_2_2_FIXTURE,
)


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    compose_file = get_docker_compose_file()
    expected_log = "http server Running on" if HARBOR_VERSION < [1, 10, 0] else "API server is serving at"
    conditions = [
        CheckDockerLogs(compose_file, expected_log, wait=3),
        lambda: time.sleep(4),
        CreateSimpleUser(),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield e2e_instance


class CreateSimpleUser(LazyFunction):
    def __call__(self, *args, **kwargs):
        requests.post(
            URL + USERS_URL,
            auth=("admin", "Harbor12345"),
            json={
                "username": "NotAnAdmin",
                "email": "NotAnAdmin@goharbor.io",
                "password": "Str0ngPassw0rd",
                "realname": "Not An Admin",
            },
            verify=False,
        )


@pytest.fixture(scope='session')
def instance():
    content = INSTANCE.copy()
    if os.environ.get('HARBOR_USE_SSL'):
        content['tls_ca_cert'] = os.path.join(HERE, 'compose', 'common', 'cert', 'ca.crt')
    return content


@pytest.fixture(scope='session')
def admin_instance():
    content = ADMIN_INSTANCE.copy()
    if os.environ.get('HARBOR_USE_SSL'):
        content['tls_ca_cert'] = os.path.join(HERE, 'compose', 'common', 'cert', 'ca.crt')
    return content


@pytest.fixture(scope='session')
def e2e_instance():
    content = INSTANCE.copy()
    if os.environ.get('HARBOR_USE_SSL'):
        content['tls_ca_cert'] = "/home/harbor/tests/compose/common/cert/ca.crt"
    return content


@pytest.fixture
def harbor_check(admin_instance):
    check = HarborCheck('harbor', {}, [admin_instance])
    return check


@pytest.fixture
def harbor_api(harbor_check, admin_instance, patch_requests):
    yield HarborAPI(URL, harbor_check.http)


@pytest.fixture
def patch_requests():
    with patch("requests.api.request", side_effect=mocked_requests):
        yield


def get_docker_compose_file():
    harbor_version = os.environ['HARBOR_VERSION']
    harbor_folder = 'harbor-{}'.format(harbor_version)
    return os.path.join(HERE, 'compose', harbor_folder, 'docker-compose.yml')


def mocked_requests(_, *args, **kwargs):
    def match(url, *candidates_url):
        for c in candidates_url:
            if url == c.format(base_url=URL):
                return True
        return False

    if match(args[0], LOGIN_PRE_1_7_URL, LOGIN_URL):
        return MockResponse()
    elif match(args[0], HEALTH_URL) and HARBOR_VERSION >= VERSION_1_8:
        return MockResponse(json_data=HEALTH_FIXTURE)
    elif match(args[0], PING_URL):
        return MockResponse('Pong')
    elif match(args[0], CHARTREPO_HEALTH_URL) and HARBOR_VERSION >= VERSION_1_6:
        return MockResponse(json_data=CHARTREPO_HEALTH_FIXTURE)
    elif match(args[0], PROJECTS_URL):
        return MockResponse(json_data=PROJECTS_FIXTURE)
    elif match(args[0], REGISTRIES_PRE_1_8_URL, REGISTRIES_URL):
        if HARBOR_VERSION >= VERSION_1_8:
            return MockResponse(json_data=REGISTRIES_FIXTURE)
        return MockResponse(json_data=REGISTRIES_PRE_1_8_FIXTURE)
    elif match(args[0], REGISTRIES_PING_PRE_1_8_URL, REGISTRIES_PING_URL):
        return MockResponse()
    elif match(args[0], VOLUME_INFO_URL):
        if HARBOR_VERSION < VERSION_2_2:
            return MockResponse(json_data=VOLUME_INFO_PRE_2_2_FIXTURE)
        return MockResponse(json_data=VOLUME_INFO_FIXTURE)
    elif match(args[0], SYSTEM_INFO_URL):
        return MockResponse(json_data=SYSTEM_INFO_FIXTURE)

    return MockResponse(status_code=404)
