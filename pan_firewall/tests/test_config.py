# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck

from .common import PANORAMA_INSTANCE, STATIC_INSTANCE


def run(dd_run_check, instance: dict[str, Any]) -> PanFirewallCheck:
    check = PanFirewallCheck('pan_firewall', {}, [instance])
    dd_run_check(check)
    return check


@pytest.mark.parametrize(
    'base, changes',
    [
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
        pytest.param(
            {}, {'panorama_host': 'pan.example.com', 'panorama_api_key': 'k'}, id='panorama-without-static-credentials'
        ),
    ],
)
def test_valid_config_loads(dd_run_check, base, changes):
    instance = {**copy.deepcopy(base), **changes}
    instance = {k: v for k, v in instance.items() if v is not None}

    run(dd_run_check, instance)


@pytest.mark.parametrize(
    'base, changes, message',
    [
        pytest.param(
            STATIC_INSTANCE, {'firewalls': None}, 'One of `firewalls` or `panorama_host` is required', id='neither-mode'
        ),
        pytest.param(STATIC_INSTANCE, {'panorama_host': 'pan.example.com'}, 'not both', id='both-modes'),
        pytest.param(
            STATIC_INSTANCE, {'firewalls': ['fw.example.com']}, '`fw.example.com` is not a valid IP', id='non-ip-entry'
        ),
        pytest.param(
            STATIC_INSTANCE,
            {'firewalls': ['192.0.2.10', '192.0.2.10']},
            '`192.0.2.10` is duplicated',
            id='duplicate-ip',
        ),
        pytest.param(
            STATIC_INSTANCE,
            {'firewall_credentials': [{'username': 'u'}]},
            'entry 0 must set',
            id='credential-username-only',
        ),
        pytest.param(
            STATIC_INSTANCE,
            {'firewall_credentials': [{'username': 'u', 'password': 'p', 'api_key': 'k'}]},
            'entry 0 must set',
            id='credential-both',
        ),
        pytest.param(
            STATIC_INSTANCE,
            {'firewall_credentials': [{'cidr': '192.0.2.0/99', 'username': 'u', 'password': 'p'}]},
            'invalid `cidr`: `192.0.2.0/99`',
            id='bad-cidr',
        ),
        pytest.param(
            STATIC_INSTANCE,
            {'firewall_credentials': [{'cidr': '10.0.0.0/8', 'username': 'u', 'password': 'p'}]},
            'matches the firewall `192.0.2.10`',
            id='unmatched-ip',
        ),
        pytest.param(STATIC_INSTANCE, {'max_concurrency': 0}, 'max_concurrency', id='max-concurrency-zero'),
        pytest.param(STATIC_INSTANCE, {'report_top_n': 0}, 'report_top_n', id='report-top-n-zero'),
        pytest.param(
            STATIC_INSTANCE,
            {'security_rule_filter': ['^ok-', '[unclosed']},
            r'`security_rule_filter` entry `\[unclosed` is not a valid regular expression',
            id='bad-rule-filter-pattern',
        ),
        pytest.param(PANORAMA_INSTANCE, {'panorama_api_key': None}, '`panorama_host` requires', id='no-auth'),
        pytest.param(
            PANORAMA_INSTANCE,
            {'panorama_username': 'u', 'panorama_password': 'p'},
            '`panorama_host` requires',
            id='login-and-key',
        ),
        pytest.param(
            PANORAMA_INSTANCE, {'firewall_ips': {'include': ['not-a-cidr']}}, 'firewall_ips.include', id='bad-include'
        ),
        pytest.param(PANORAMA_INSTANCE, {'firewall_ip_overrides': {'SERIAL1': 'host'}}, '`SERIAL1`', id='bad-override'),
    ],
)
def test_invalid_config(dd_run_check, base, changes, message):
    instance = {**copy.deepcopy(base), **changes}
    instance = {k: v for k, v in instance.items() if v is not None}

    with pytest.raises(Exception, match=message):
        run(dd_run_check, instance)
