# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck

from .common import CREDENTIALS, PANORAMA_INSTANCE, STATIC_INSTANCE


def run(dd_run_check, instance: dict[str, Any]) -> PanFirewallCheck:
    check = PanFirewallCheck('pan_firewall', {}, [instance])
    dd_run_check(check)
    return check


@pytest.mark.parametrize(
    'base, changes',
    [
        pytest.param(STATIC_INSTANCE, {}, id='static'),
        pytest.param(PANORAMA_INSTANCE, {}, id='panorama-api-key'),
        pytest.param(
            PANORAMA_INSTANCE,
            {'panorama_api_key': None, 'panorama_username': 'u', 'panorama_password': 'p'},
            id='panorama-login',
        ),
        pytest.param(
            STATIC_INSTANCE,
            {
                'firewalls': ['192.0.2.10', '198.51.100.7', '2001:db8::1'],
                'firewall_credentials': [
                    {'cidr': '192.0.2.0/24', 'username': 'u', 'password': 'p'},
                    {'cidr': '198.51.100.0/24', 'api_key': 'k'},
                    {'api_key': 'catch-all'},
                ],
            },
            id='static-cidr-credentials-and-ipv6',
        ),
    ],
)
def test_valid_config_loads(dd_run_check, base, changes):
    instance = {**copy.deepcopy(base), **changes}
    instance = {k: v for k, v in instance.items() if v is not None}

    check = run(dd_run_check, instance)

    assert bool(check.config.firewalls) != bool(check.config.panorama_host)


@pytest.mark.parametrize(
    'changes, message',
    [
        pytest.param({'firewalls': None}, 'One of `firewalls` or `panorama_host` is required', id='neither-mode'),
        pytest.param({'firewalls': []}, 'One of `firewalls` or `panorama_host` is required', id='empty-firewalls'),
        pytest.param({'panorama_host': 'pan.example.com'}, 'not both', id='both-modes'),
        pytest.param({'firewalls': ['fw.example.com']}, '`fw.example.com` is not a valid IP', id='non-ip-entry'),
        pytest.param({'firewalls': ['192.0.2.10', '192.0.2.10']}, '`192.0.2.10` is duplicated', id='duplicate-ip'),
        pytest.param({'firewall_credentials': [{'cidr': '192.0.2.0/24'}]}, 'entry 0 must set', id='credential-empty'),
        pytest.param({'firewall_credentials': [{'username': 'u'}]}, 'entry 0 must set', id='credential-username-only'),
        pytest.param(
            {'firewall_credentials': [{'username': 'u', 'password': 'p', 'api_key': 'k'}]},
            'entry 0 must set',
            id='credential-both',
        ),
        pytest.param(
            {'firewall_credentials': [{'cidr': '192.0.2.0/99', 'username': 'u', 'password': 'p'}]},
            'invalid `cidr`: `192.0.2.0/99`',
            id='bad-cidr',
        ),
        pytest.param(
            {'firewall_credentials': [{'cidr': '10.0.0.0/8', 'username': 'u', 'password': 'p'}]},
            'matches the firewall `192.0.2.10`',
            id='unmatched-ip',
        ),
        pytest.param({'max_concurrency': 0}, 'max_concurrency', id='max-concurrency-zero'),
        pytest.param({'report_top_n': 0}, 'report_top_n', id='report-top-n-zero'),
    ],
)
def test_invalid_static_config(dd_run_check, changes, message):
    instance = {**copy.deepcopy(STATIC_INSTANCE), **changes}
    instance = {k: v for k, v in instance.items() if v is not None}

    with pytest.raises(Exception, match=message):
        run(dd_run_check, instance)


@pytest.mark.parametrize(
    'changes, message',
    [
        pytest.param({'panorama_api_key': None}, '`panorama_host` requires', id='no-auth'),
        pytest.param(
            {'panorama_api_key': None, 'panorama_username': 'u'},
            '`panorama_host` requires',
            id='username-without-password',
        ),
        pytest.param(
            {'panorama_username': 'u', 'panorama_password': 'p'}, '`panorama_host` requires', id='login-and-key'
        ),
        pytest.param({'firewall_ips': {'include': ['not-a-cidr']}}, 'firewall_ips.include', id='bad-include'),
        pytest.param({'firewall_ip_overrides': {'SERIAL1': 'host'}}, '`SERIAL1`', id='bad-override'),
    ],
)
def test_invalid_panorama_config(dd_run_check, changes, message):
    instance = {**copy.deepcopy(PANORAMA_INSTANCE), **changes}
    instance = {k: v for k, v in instance.items() if v is not None}

    with pytest.raises(Exception, match=message):
        run(dd_run_check, instance)


def test_credentials_are_not_required_without_static_firewalls(dd_run_check):
    instance = {'panorama_host': 'pan.example.com', 'panorama_api_key': 'k'}

    run(dd_run_check, instance)


def test_first_matching_credential_wins(dd_run_check):
    from datadog_checks.pan_firewall.config_models.validators import find_credential

    instance = {
        'firewalls': ['10.1.2.3'],
        'firewall_credentials': [
            {'cidr': '10.1.0.0/16', 'username': 'first', 'password': 'p'},
            {'cidr': '10.0.0.0/8', 'username': 'second', 'password': 'p'},
            *CREDENTIALS,
        ],
    }
    credentials = list(run(dd_run_check, instance).config.firewall_credentials)

    assert find_credential('10.1.2.3', credentials).username == 'first'
    assert find_credential('10.9.9.9', credentials).username == 'second'
    assert find_credential('172.16.0.1', credentials).username == 'dummy-user'
