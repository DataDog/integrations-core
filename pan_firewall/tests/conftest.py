# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from typing import Any

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS

from .common import (
    CREDENTIALS,
    E2E_FIREWALL_IPS,
    E2E_FIREWALL_SERIALS,
    E2E_NETWORK,
    E2E_PANORAMA_IP,
    E2E_SUBNET,
    INSTANCE,
    PANORAMA_CREDENTIALS,
    build_lab_instance,
)
from .fake_panos import FakePanos

COMPOSE_FILE = os.path.join(get_here(), 'docker', 'docker-compose.yaml')


SERVICES = ('fw-a', 'fw-b', 'panorama')


def docker_environment():
    """Start the docker fakes (two firewalls and a Panorama) and yield an Agent instance per mode.

    The static instance polls both fake firewalls; the Panorama one discovers them through the fake Panorama, whose
    reported 10.60.x addresses are not reachable, so `firewall_ip_overrides` points each serial at its fake.
    """
    firewalls = list(E2E_FIREWALL_IPS.values())
    env_vars = {
        'PANOS_USERNAME': CREDENTIALS[0]['username'],
        'PANOS_PASSWORD': CREDENTIALS[0]['password'],
        'PANORAMA_USERNAME': PANORAMA_CREDENTIALS['username'],
        'PANORAMA_PASSWORD': PANORAMA_CREDENTIALS['password'],
        'FW_A_IP': E2E_FIREWALL_IPS['fw-a'],
        'FW_B_IP': E2E_FIREWALL_IPS['fw-b'],
        'PANORAMA_IP': E2E_PANORAMA_IP,
        'E2E_SUBNET': E2E_SUBNET,
    }
    static = {'firewalls': firewalls, 'firewall_credentials': CREDENTIALS, 'tls_verify': False}
    panorama = {
        'panorama_host': E2E_PANORAMA_IP,
        'panorama_username': PANORAMA_CREDENTIALS['username'],
        'panorama_password': PANORAMA_CREDENTIALS['password'],
        'firewall_credentials': CREDENTIALS,
        'firewall_ip_overrides': {E2E_FIREWALL_SERIALS[name]: ip for name, ip in E2E_FIREWALL_IPS.items()},
        'tls_verify': False,
    }
    ready = [CheckDockerLogs(COMPOSE_FILE, 'Running on all addresses', service=service) for service in SERVICES]
    with docker_run(compose_file=COMPOSE_FILE, build=True, conditions=ready, env_vars=env_vars):
        yield {'instances': [static, panorama]}, {'docker_network': E2E_NETWORK}


@pytest.fixture(scope='session')
def dd_environment():
    if os.environ.get('USE_PANOS_LAB'):
        # Lab mode: one instance built from environment variables only, no docker fakes. Set the variables in
        # your own terminal (the password is read silently and never written to a file or to the shell history):
        #
        #   read -rs "PANOS_PASSWORD?Password: "
        #   export PANOS_PASSWORD PANOS_LAB_HOSTS=<ip1>,<ip2> PANOS_LAB_USERNAME=<username>
        #
        # then run `ddev env start pan_firewall py3.13-lab`, `ddev env agent pan_firewall py3.13-lab check` and
        # `ddev env test pan_firewall py3.13-lab`. The instance is never logged or printed: it holds the password.
        #
        # Panorama mode (setting PANOS_LAB_PANORAMA_HOST selects it, and PANOS_LAB_HOSTS is then not needed): the
        # firewalls are discovered from Panorama, so set its host and credentials, plus the firewalls' own. Read
        # BOTH passwords silently, in your own terminal:
        #
        #   read -rs "PANOS_LAB_PANORAMA_PASSWORD?Panorama password: "
        #   read -rs "PANOS_PASSWORD?Firewall password: "
        #   export PANOS_LAB_PANORAMA_PASSWORD PANOS_PASSWORD
        #   export PANOS_LAB_PANORAMA_HOST=<host> PANOS_LAB_PANORAMA_USERNAME=<username> PANOS_LAB_USERNAME=<username>
        #   export PANOS_LAB_FIREWALL_OVERRIDES=<serial>=<reachable-ip>,<serial>=<reachable-ip>
        #
        # PANOS_LAB_FIREWALL_OVERRIDES is only needed when the IPs Panorama reports are not reachable from where the
        # Agent runs. Then run the `lab-panorama` env (its own name: hatch cannot make one env depend on either of
        # two variables):
        #
        #   ddev env start pan_firewall py3.13-lab-panorama
        #   ddev env test pan_firewall py3.13-lab-panorama
        #   ddev env stop pan_firewall py3.13-lab-panorama
        yield {'instances': [build_lab_instance()]}
    else:
        # The docker environment is added in a later task.
        yield from docker_environment()


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(INSTANCE)


@pytest.fixture(autouse=True)
def fake_panos(monkeypatch, datadog_agent) -> FakePanos:
    """Serve every HTTP POST from the fake PAN-OS API, so no unit test reaches the network.

    Requesting `datadog_agent` resets the stubbed persistent cache between tests.
    """
    fake = FakePanos()
    monkeypatch.setattr(RequestsWrapper, 'post', lambda _self, url, **options: fake.post(url, **options))
    return fake


@pytest.fixture
def real_collectors():
    """Request it to keep the real collectors registered, which the other tests replace with stubs."""


@pytest.fixture(autouse=True)
def only_test_collectors(request, monkeypatch):
    """Start every test with an empty collector registry, so a test runs the collectors it registers and no others."""
    if 'real_collectors' not in request.fixturenames:
        for name in list(COLLECT_FUNCTIONS):
            monkeypatch.delitem(COLLECT_FUNCTIONS, name)
