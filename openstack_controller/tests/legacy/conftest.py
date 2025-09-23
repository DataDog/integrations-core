# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.ssh_tunnel import socks_proxy
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.openstack_controller.legacy.openstack_controller_legacy import OpenStackControllerLegacyCheck
from tests.legacy.common import CHECK_NAME, CONFIG_FILE_INSTANCE, USE_OPENSTACK_SANDBOX


@pytest.fixture(scope='session')
def dd_environment():
    if USE_OPENSTACK_SANDBOX:
        with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
            ip = outputs['ip']['value']
            internal_ip = outputs['internal_ip']['value']
            private_key = outputs['ssh_private_key']['value']
            instance = {
                'name': 'test',
                'keystone_server_url': 'http://{}/identity/v3'.format(internal_ip),
                'user': {'name': 'admin', 'password': 'labstack', 'domain': {'id': 'default'}},
                'ssl_verify': False,
            }
            with socks_proxy(ip, 'ubuntu', private_key) as socks:
                print("socks: %s", socks)
                socks_ip, socks_port = socks
                agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
                yield instance, agent_config
    else:
        compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
        conditions = [
            CheckDockerLogs(identifier='openstack-keystone', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-nova', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-neutron', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-ironic', patterns=['server running']),
        ]
        with docker_run(compose_file, conditions=conditions):
            instance = {
                'name': 'test',
                'keystone_server_url': 'http://127.0.0.1:8080/identity/v3',
                'user': {'name': 'admin', 'password': 'labstack', 'domain': {'id': 'default'}},
                'ssl_verify': False,
            }
            yield instance


@pytest.fixture
def instance():
    return CONFIG_FILE_INSTANCE


@pytest.fixture
def check(instance):
    return OpenStackControllerLegacyCheck(CHECK_NAME, {}, [instance])


@pytest.fixture
def requests_wrapper():
    instance = {'timeout': 10, 'ssl_verify': False}
    yield RequestsWrapper(instance, {})
