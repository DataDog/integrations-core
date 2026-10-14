# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / 'fixtures'
SYNTHETIC = FIXTURES / 'synthetic'

CREDENTIALS = [{'username': 'dummy-user', 'password': 'dummy-password'}]

# The unit fake's firewalls (`fake_panos.FIREWALL_SETS`); FW_C_IP answers nothing.
FW_A_IP = '192.0.2.10'
FW_B_IP = '192.0.2.11'
FW_C_IP = '192.0.2.12'
FW_A_SERIAL = '007955000930601'
FW_B_SERIAL = '007955000930602'
SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'
# The collectors `helpers.register_stubs` replaces with stubs.
STUBS = ('bgp', 'dataplane', 'interfaces', 'system_resources')

BASE_TAGS = [f'device_ip:{FW_A_IP}', 'device_namespace:default', 'device_vendor:paloaltonetworks', 'team:test']
FW_A_TAGS = sorted(
    [
        *BASE_TAGS,
        f'device_id:{FW_A_SERIAL}',
        'device_hostname:fw-a',
        f'device_serial:{FW_A_SERIAL}',
        'device_model:PA-VM',
        'device_family:vm',
        'os_version:11.1.13-h12',
        'multi_vsys:false',
        'advanced_routing:false',
        f'dd.internal.resource:ndm_device:{FW_A_SERIAL}',
        f'dd.internal.resource:ndm_device_user_tags:{FW_A_SERIAL}',
    ]
)

STATIC_INSTANCE = {
    'firewalls': ['192.0.2.10'],
    'firewall_credentials': CREDENTIALS,
}

PANORAMA_INSTANCE = {
    'panorama_host': 'panorama.example.com',
    'panorama_api_key': 'dummy-api-key',
    'firewall_credentials': CREDENTIALS,
}

# The docker fakes (see `docker/docker-compose.yaml`): the Agent container joins the `pan-firewall-e2e` network and
# reaches each fake on port 443 at its own address.
E2E_NETWORK = 'pan-firewall-e2e'
DEFAULT_E2E_SUBNET = '172.29.84.0/24'


def e2e_addresses(subnet: str) -> tuple[dict[str, str], str]:
    """Derive the fake firewalls' and Panorama's addresses (offsets 10, 11 and 12) from the E2E subnet."""
    network = ipaddress.ip_network(subnet, strict=False)
    if network.version != 4 or network.num_addresses < 16:
        pytest.fail(f'PANOS_E2E_SUBNET must be an IPv4 network with at least 16 addresses, got {subnet}')
    first = network.network_address
    return {'fw-a': str(first + 10), 'fw-b': str(first + 11)}, str(first + 12)


# Set PANOS_E2E_SUBNET when the default subnet overlaps a network of your machine; docker-compose.yaml receives it
# from `dd_environment` through its own `E2E_SUBNET` variable.
E2E_SUBNET = os.environ.get('PANOS_E2E_SUBNET', DEFAULT_E2E_SUBNET)
E2E_FIREWALL_IPS, E2E_PANORAMA_IP = e2e_addresses(E2E_SUBNET)
PANORAMA_CREDENTIALS = {'username': 'dummy-panorama-user', 'password': 'dummy-panorama-password'}
# The serials the synthetic Panorama device list gives the two firewalls (the real P1 entries).
E2E_FIREWALL_SERIALS = {'fw-a': '007955000930601', 'fw-b': '007955000930602'}

# `static` or `panorama`, set by the hatch env (`py3.13-lab` and `py3.13-lab-panorama`), never by hand.
LAB_MODE_VAR = 'PANOS_LAB_MODE'
LAB_MODES = ('static', 'panorama')
LAB_HOSTS_VAR = 'PANOS_LAB_HOSTS'
LAB_USERNAME_VAR = 'PANOS_LAB_USERNAME'
LAB_PASSWORD_VAR = 'PANOS_PASSWORD'
LAB_COLLECT_ALL_VAR = 'PANOS_LAB_COLLECT_ALL'
# Panorama mode: these replace the static `PANOS_LAB_HOSTS`.
LAB_PANORAMA_HOST_VAR = 'PANOS_LAB_PANORAMA_HOST'
LAB_PANORAMA_USERNAME_VAR = 'PANOS_LAB_PANORAMA_USERNAME'
LAB_PANORAMA_PASSWORD_VAR = 'PANOS_LAB_PANORAMA_PASSWORD'
LAB_OVERRIDES_VAR = 'PANOS_LAB_FIREWALL_OVERRIDES'


def lab_hosts(environ: Mapping[str, str] = os.environ) -> list[str]:
    return [host.strip() for host in environ.get(LAB_HOSTS_VAR, '').split(',') if host.strip()]


def lab_panorama_host(environ: Mapping[str, str] = os.environ) -> str | None:
    return environ.get(LAB_PANORAMA_HOST_VAR) or None


def lab_mode(environ: Mapping[str, str] = os.environ) -> str:
    """Return the lab mode from `PANOS_LAB_MODE`; fail naming the variable (not echoing its value) if it is invalid."""
    mode = environ.get(LAB_MODE_VAR, '')
    if mode not in LAB_MODES:
        pytest.fail(f'{LAB_MODE_VAR} must be one of: {", ".join(LAB_MODES)} (the py3.13-lab* hatch envs set it)')
    return mode


def _fail_missing(names: list[str]) -> None:
    pytest.fail(f'USE_PANOS_LAB is set but these environment variables are missing or empty: {", ".join(names)}')


def _parse_overrides(environ: Mapping[str, str]) -> dict[str, str]:
    """Parse `serial=ip,serial=ip`; a malformed string fails naming the variable, never echoing its value."""
    overrides = {}
    for entry in environ.get(LAB_OVERRIDES_VAR, '').split(','):
        if not entry.strip():
            continue
        serial, separator, address = (part.strip() for part in entry.partition('='))
        try:
            ipaddress.ip_address(address)
        except ValueError:
            address = ''
        if not (separator and serial and address and '=' not in address):
            pytest.fail(f'{LAB_OVERRIDES_VAR} is malformed: expected `serial=ip,serial=ip`')
        overrides[serial] = address
    return overrides


def build_lab_instance(environ: Mapping[str, str] = os.environ) -> dict[str, Any]:
    """Build the single lab instance from the environment only; fail naming (never showing) missing variables."""
    instance: dict[str, Any]
    if lab_mode(environ) == 'panorama':
        required = (
            LAB_PANORAMA_HOST_VAR,
            LAB_PANORAMA_USERNAME_VAR,
            LAB_PANORAMA_PASSWORD_VAR,
            LAB_USERNAME_VAR,
            LAB_PASSWORD_VAR,
        )
        if missing := [name for name in required if not environ.get(name)]:
            _fail_missing(missing)
        instance = {
            'panorama_host': environ[LAB_PANORAMA_HOST_VAR],
            'panorama_username': environ[LAB_PANORAMA_USERNAME_VAR],
            'panorama_password': environ[LAB_PANORAMA_PASSWORD_VAR],
            'firewall_credentials': [{'username': environ[LAB_USERNAME_VAR], 'password': environ[LAB_PASSWORD_VAR]}],
            'tls_verify': False,
        }
        if overrides := _parse_overrides(environ):
            instance['firewall_ip_overrides'] = overrides
    else:
        missing = [name for name in (LAB_USERNAME_VAR, LAB_PASSWORD_VAR) if not environ.get(name)]
        if not lab_hosts(environ):
            missing.insert(0, LAB_HOSTS_VAR)
        if missing:
            _fail_missing(missing)
        instance = {
            'firewalls': lab_hosts(environ),
            'firewall_credentials': [{'username': environ[LAB_USERNAME_VAR], 'password': environ[LAB_PASSWORD_VAR]}],
            'tls_verify': False,
        }
    # Optional: also run the collectors that are off by default (global counters, OSPF, reports).
    if environ.get(LAB_COLLECT_ALL_VAR, '').lower() in ('1', 'true'):
        instance.update(collect_global_counters=True, collect_ospf=True, collect_reports=True)
    return instance
