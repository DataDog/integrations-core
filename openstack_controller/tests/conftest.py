# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.ssh_tunnel import socks_proxy
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here


@pytest.fixture(scope='session')
def dd_environment():
    if not os.environ.get('TF_VAR_account_json'):
        pytest.skip('TF_VAR_account_json not set')
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        if not outputs:
            # We're stopping the environment, we need fake values
            ip = internal_ip = private_key = ''
        else:
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
            if not socks:
                socks = '', 0
            socks_ip, socks_port = socks
            agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
            yield instance, agent_config
