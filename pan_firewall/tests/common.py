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

CREDENTIALS = [{'username': 'dummy-user', 'password': 'dummy-password'}]

STATIC_INSTANCE = {
    'firewalls': ['192.0.2.10'],
    'firewall_credentials': CREDENTIALS,
}

PANORAMA_INSTANCE = {
    'panorama_host': 'panorama.example.com',
    'panorama_api_key': 'dummy-api-key',
    'firewall_credentials': CREDENTIALS,
}

INSTANCE = STATIC_INSTANCE

LAB_HOSTS_VAR = 'PANOS_LAB_HOSTS'
LAB_USERNAME_VAR = 'PANOS_LAB_USERNAME'
LAB_PASSWORD_VAR = 'PANOS_PASSWORD'
LAB_COLLECT_ALL_VAR = 'PANOS_LAB_COLLECT_ALL'
# Panorama mode: set when `PANOS_LAB_PANORAMA_HOST` is, and then replaces the static `PANOS_LAB_HOSTS`.
LAB_PANORAMA_HOST_VAR = 'PANOS_LAB_PANORAMA_HOST'
LAB_PANORAMA_USERNAME_VAR = 'PANOS_LAB_PANORAMA_USERNAME'
LAB_PANORAMA_PASSWORD_VAR = 'PANOS_LAB_PANORAMA_PASSWORD'
LAB_OVERRIDES_VAR = 'PANOS_LAB_FIREWALL_OVERRIDES'


def lab_hosts(environ: Mapping[str, str] = os.environ) -> list[str]:
    return [host.strip() for host in environ.get(LAB_HOSTS_VAR, '').split(',') if host.strip()]


def lab_panorama_host(environ: Mapping[str, str] = os.environ) -> str | None:
    return environ.get(LAB_PANORAMA_HOST_VAR) or None


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
    panorama_host = lab_panorama_host(environ)
    if panorama_host:
        required = (LAB_PANORAMA_USERNAME_VAR, LAB_PANORAMA_PASSWORD_VAR, LAB_USERNAME_VAR, LAB_PASSWORD_VAR)
        if missing := [name for name in required if not environ.get(name)]:
            _fail_missing(missing)
        instance = {
            'panorama_host': panorama_host,
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
    if environ.get(LAB_COLLECT_ALL_VAR):
        instance.update(collect_global_counters=True, collect_ospf=True, collect_reports=True)
    return instance
