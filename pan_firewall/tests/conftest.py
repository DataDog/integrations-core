# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.pan_firewall import poller as poller_module
from datadog_checks.pan_firewall.collectors.base import COLLECT_FUNCTIONS
from datadog_checks.pan_firewall.panorama import IP_OVERRIDES_ENV_VAR
from datadog_checks.pan_firewall.scheduler import FirewallSchedule

from .common import (
    CREDENTIALS,
    E2E_FIREWALL_IPS,
    E2E_NETWORK,
    E2E_PANORAMA_IP,
    E2E_PANORAMA_NAMESPACE,
    E2E_SUBNET,
    PANORAMA_CREDENTIALS,
    build_lab_instance,
)
from .fake_panos import FakePanos
from .helpers import FakeClock

COMPOSE_FILE = os.path.join(get_here(), 'docker', 'docker-compose.yaml')


SERVICES = ('fw-a', 'fw-b', 'panorama')


def docker_environment():
    """Start the docker fakes (two firewalls and a Panorama) and yield an Agent instance per mode.

    The static instance polls both fake firewalls; the Panorama one discovers them through the fake Panorama, which
    reports them at their own addresses, and polls them there. The Panorama instance has its own namespace, so the two
    instances report each firewall as a different device.
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
        'namespace': E2E_PANORAMA_NAMESPACE,
        'tls_verify': False,
    }
    ready = [CheckDockerLogs(COMPOSE_FILE, 'Running on all addresses', service=service) for service in SERVICES]
    with docker_run(compose_file=COMPOSE_FILE, build=True, conditions=ready, env_vars=env_vars):
        yield {'instances': [static, panorama]}, {'docker_network': E2E_NETWORK}


@pytest.fixture(scope='session')
def dd_environment():
    if os.environ.get('USE_PANOS_LAB'):
        # Lab mode: one instance from environment variables, no docker fakes; the hatch env sets PANOS_LAB_MODE.
        # In your own terminal: `read -rs "PANOS_PASSWORD?Password: "`, then `export PANOS_PASSWORD
        # PANOS_LAB_HOSTS=<ip1>,<ip2> PANOS_LAB_USERNAME=<user>`. Then `ddev env start pan_firewall py3.13-lab`,
        # `ddev env agent pan_firewall py3.13-lab check`, and `ddev env stop pan_firewall py3.13-lab` (ddev keeps the
        # password in its env config until the stop). Panorama: env `py3.13-lab-panorama`, with PANOS_LAB_PANORAMA_HOST,
        # PANOS_LAB_PANORAMA_USERNAME and PANOS_LAB_PANORAMA_PASSWORD (read silently) instead of PANOS_LAB_HOSTS; the
        # Agent must reach the IPs Panorama reports, or PANOS_LAB_IP_OVERRIDES=<reported>=<polled>,... maps them to
        # addresses it can reach. PANOS_LAB_COLLECT_ALL=1 enables the default-off collectors.
        overrides = os.environ.get(IP_OVERRIDES_ENV_VAR)
        yield (
            {'instances': [build_lab_instance()]},
            {'env_vars': {IP_OVERRIDES_ENV_VAR: overrides} if overrides else {}},
        )
    else:
        yield from docker_environment()


@pytest.fixture(autouse=True)
def fake_panos(mocker, datadog_agent) -> FakePanos:
    """Serve every HTTP POST from the fake PAN-OS API, so no unit test reaches the network. `RequestsWrapper` runs
    as in production (timeout, headers, TLS options, session); only the session's `post` is replaced.

    Requesting `datadog_agent` resets the stubbed persistent cache between tests.
    """
    fake = FakePanos()
    mocker.patch('requests.Session.post', side_effect=fake.post)
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


@pytest.fixture
def schedule_clock(monkeypatch) -> FakeClock:
    """Run every poller's schedule on a fake clock; move time by setting the returned clock's `now`."""
    clock = FakeClock()
    monkeypatch.setattr(poller_module, 'FirewallSchedule', lambda: FirewallSchedule(clock))
    return clock
