# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.ssh_tunnel import socks_proxy
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import CHECK_NAME, CONFIG_FILE_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
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
            socks_ip, socks_port = socks
            agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
            yield instance, agent_config


@pytest.fixture
def instance():
    return CONFIG_FILE_INSTANCE


@pytest.fixture
def check(instance):
    return OpenStackControllerCheck(CHECK_NAME, {}, [instance])


@pytest.fixture
def requests_wrapper():
    instance = {'timeout': 10, 'ssl_verify': False}
    yield RequestsWrapper(instance, {})
