# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_here

CHECK_NAME = 'ibm_hmc'

# The e2e runs the check inside the Agent container, which mounts this
# integration at /home/ibm_hmc. The committed host key of the e2e container
# lets host key verification pass without touching the Agent user's own known
# hosts file.
E2E_INSTANCE = {
    'host': '127.0.0.1',
    'port': 8022,
    'username': 'root',
    'password': 'datadog-hmc-e2e',
    'known_hosts_file': '/home/ibm_hmc/tests/compose/known_hosts',
}


@pytest.fixture
def instance():
    return {
        'host': 'hmc.example.com',
        'port': 22,
        'username': 'hscroot',
        'password': 'abcdef',
    }


@pytest.fixture
def e2e_instance():
    return dict(E2E_INSTANCE)


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        env_vars={'ROOT_PASSWORD': 'datadog-hmc-e2e'},
        log_patterns='Server listening on',
    ):
        yield E2E_INSTANCE
