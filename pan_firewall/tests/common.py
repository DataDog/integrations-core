# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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


def lab_hosts(environ: Mapping[str, str] = os.environ) -> list[str]:
    return [host.strip() for host in environ.get(LAB_HOSTS_VAR, '').split(',') if host.strip()]


def build_lab_instance(environ: Mapping[str, str] = os.environ) -> dict[str, Any]:
    """Build the single lab instance from the environment only; fail naming (never showing) missing variables."""
    missing = [name for name in (LAB_HOSTS_VAR, LAB_USERNAME_VAR, LAB_PASSWORD_VAR) if not environ.get(name)]
    if not lab_hosts(environ):
        missing = sorted({*missing, LAB_HOSTS_VAR}, key=(LAB_HOSTS_VAR, LAB_USERNAME_VAR, LAB_PASSWORD_VAR).index)
    if missing:
        pytest.fail(f'USE_PANOS_LAB is set but these environment variables are missing or empty: {", ".join(missing)}')
    instance: dict[str, Any] = {
        'firewalls': lab_hosts(environ),
        'firewall_credentials': [{'username': environ[LAB_USERNAME_VAR], 'password': environ[LAB_PASSWORD_VAR]}],
        'tls_verify': False,
    }
    # Optional: also run the collectors that are off by default (global counters, OSPF, reports).
    if environ.get(LAB_COLLECT_ALL_VAR):
        instance.update(collect_global_counters=True, collect_ospf=True, collect_reports=True)
    return instance
