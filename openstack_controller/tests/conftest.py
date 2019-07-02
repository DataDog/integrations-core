# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.ssh_tunnel import find_free_port, socks_proxy
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here


@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        ip = outputs['ip']['value']
        internal_ip = outputs['internal_ip']['value']
        private_key = outputs['ssh_private_key']['value']
        socks_port = find_free_port()
        instance = {
            'name': 'test',
            'keystone_server_url': 'http://{}/identity/v3'.format(internal_ip),
            'user': {'name': 'admin', 'password': 'labstack', 'domain': {'id': 'default'}},
            'ssl_verify': False,
        }
        agent_config = {'proxy': {'http': 'socks5://localhost:{}'.format(socks_port)}}
        with socks_proxy(socks_port, ip, 'ubuntu', private_key):
            yield instance, agent_config
