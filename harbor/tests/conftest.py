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
from datadog_checks.harbor.common import API_VERSION_URL, SYSTEM_INFO_URL

from .common import (
    ADMIN_INSTANCE,
    HERE,
    INSTANCE,
    SYSTEM_INFO_FIXTURE,
    URL,
    USERS_PATH,
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
def harbor_check(admin_instance, fake_http):
    check = HarborCheck('harbor', {}, [admin_instance])
    return check


@pytest.fixture
def harbor_api(harbor_check, fake_http_response):
    fake_http_response(API_VERSION_URL.format(base_url=URL), status_code=404)
    fake_http_response(SYSTEM_INFO_URL.format(base_url=URL), json_data=SYSTEM_INFO_FIXTURE)
    return HarborAPI(URL, harbor_check.http)


def get_docker_compose_file():
    harbor_version = os.environ['HARBOR_VERSION']
    harbor_folder = 'harbor-{}'.format(harbor_version)
    return os.path.join(HERE, 'compose', harbor_folder, 'docker-compose.yml')
