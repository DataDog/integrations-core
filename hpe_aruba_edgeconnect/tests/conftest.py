# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import ssl
from urllib.request import urlopen

import pytest

from datadog_checks.dev import WaitFor, docker_run, get_docker_hostname, get_here
from datadog_checks.dev.utils import find_free_port


@pytest.fixture(scope='session')
def logger() -> logging.Logger:
    return logging.getLogger('hpe_aruba_edgeconnect.tests')


HERE = get_here()
HOST = get_docker_hostname()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


@pytest.fixture(scope='session')
def dd_environment(instance, dd_save_state):
    orch_port = find_free_port(HOST)
    appliance_port = find_free_port(HOST)
    orch_ip = f'{HOST}:{orch_port}'
    appliance_ip = f'{HOST}:{appliance_port}'

    def _ready():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urlopen(f'https://{orch_ip}/health', timeout=2, context=ctx)
        urlopen(f'https://{appliance_ip}/health', timeout=2, context=ctx)

    inst = instance(orch_ip, connect_timeout=2)
    dd_save_state('e2e_instance', inst)

    with docker_run(
        compose_file=COMPOSE_FILE,
        build=True,
        conditions=[WaitFor(_ready, attempts=60, wait=1)],
        env_vars={
            'HOST_PORT': str(orch_port),
            'APPLIANCE_PORT': str(appliance_port),
            'ORCH_USERNAME': 'admin',
            'ORCH_PASSWORD': '',
            'APPLIANCE_USERNAME': 'admin',
            'APPLIANCE_PASSWORD': '',
            'APPLIANCE_IP': appliance_ip,
        },
    ):
        yield {'instances': [inst]}


@pytest.fixture(scope='session')
def instance():
    def builder(
        orch_ip: str,
        username: str = 'admin',
        password: str = '',
        appliance_ips=None,
        appliance_credentials=None,
        **kwargs,
    ) -> dict:
        inst = {
            'orch_ip': orch_ip,
            'username': username,
            'password': password,
            'tls_verify': False,
            **kwargs,
        }
        if appliance_ips is not None:
            inst['appliance_ips'] = appliance_ips if isinstance(appliance_ips, dict) else {'include': appliance_ips}
        if appliance_credentials is not None:
            inst['appliance_credentials'] = appliance_credentials
        return inst

    return builder
