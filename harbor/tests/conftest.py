# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.harbor import HarborCheck
from datadog_checks.harbor.api import HarborAPI
from datadog_checks.harbor.common import (
    API_VERSION_URL,
    CHARTREPO_HEALTH_URL,
    HEALTH_URL,
    PING_URL,
    PROJECTS_URL,
    REGISTRIES_PING_URL,
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
    SYSTEM_INFO_FIXTURE,
    URL,
    USERS_PATH,
    VERSION_2_2,
    VOLUME_INFO_FIXTURE,
    VOLUME_INFO_PRE_2_2_FIXTURE,
)


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    compose_file = get_docker_compose_file()
    expected_log = "http server Running on"
    conditions = [
        CheckDockerLogs(compose_file, expected_log, wait=3, service='core'),
        WaitFor(create_simple_user, wait=5),
    ]
    e2e_metadata = {}
    if os.environ.get('HARBOR_USE_SSL'):
        cert_dir = os.path.join(HERE, 'compose', 'common', 'cert')
        e2e_metadata['docker_volumes'] = ['{}:/home/harbor/tests/compose/common/cert'.format(cert_dir)]
    with docker_run(compose_file, conditions=conditions, attempts=5, wait_for_health=True):
        yield e2e_instance, e2e_metadata


def create_simple_user():
    response = requests.post(
        URL + USERS_PATH,
        auth=("admin", "Harbor12345"),
        json={
            "username": "NotAnAdmin",
            "email": "NotAnAdmin@goharbor.io",
            "password": "Str0ngPassw0rd",
            "realname": "Not An Admin",
        },
        verify=False,
    )
    # A conflict means an earlier attempt or a reused environment already created the user.
    if response.status_code != 409:
        response.raise_for_status()


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
def harbor_api(harbor_check, admin_instance, harbor_responses):
    yield HarborAPI(URL, harbor_check.http)


@pytest.fixture
def harbor_responses(fake_http_response):
    def register(url_template, **response):
        fake_http_response(url_template.format(base_url=URL), **response)

    # The version endpoint only exists from Harbor 2.0. A 404 keeps the legacy, unversioned API paths.
    register(API_VERSION_URL, status_code=404)
    register(HEALTH_URL, json_data=HEALTH_FIXTURE)
    register(PING_URL, content='Pong')
    register(CHARTREPO_HEALTH_URL, json_data=CHARTREPO_HEALTH_FIXTURE)
    register(PROJECTS_URL, json_data=PROJECTS_FIXTURE)
    register(REGISTRIES_URL, json_data=REGISTRIES_FIXTURE)
    register(REGISTRIES_PING_URL, method='POST')
    register(
        VOLUME_INFO_URL,
        json_data=VOLUME_INFO_PRE_2_2_FIXTURE if HARBOR_VERSION < VERSION_2_2 else VOLUME_INFO_FIXTURE,
    )
    register(SYSTEM_INFO_URL, json_data=SYSTEM_INFO_FIXTURE)


def get_docker_compose_file():
    harbor_version = os.environ['HARBOR_VERSION']
    harbor_folder = 'harbor-{}'.format(harbor_version)
    return os.path.join(HERE, 'compose', harbor_folder, 'docker-compose.yml')
