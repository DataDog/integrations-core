# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck

from .common import PANORAMA_INSTANCE, STATIC_INSTANCE

pytestmark = pytest.mark.unit


def run(dd_run_check, instance: dict[str, Any]) -> PanFirewallCheck:
    check = PanFirewallCheck('pan_firewall', {}, [instance])
    dd_run_check(check)
    return check


def instance_with(base, changes):
    """`base` with `changes` applied; a change to None removes the option."""
    instance = {**copy.deepcopy(base), **changes}
    return {k: v for k, v in instance.items() if v is not None}


def test_static_config_with_cidr_credentials_and_ipv6_polls_each_firewall_with_its_entry(dd_run_check, fake_panos):
    instance = {
        'firewalls': ['192.0.2.10', '198.51.100.7', '2001:db8::1'],
        'firewall_credentials': [
            {'cidr': '192.0.2.0/24', 'username': 'u', 'password': 'p'},
            {'cidr': '198.51.100.0/24', 'api_key': 'k'},
            {'api_key': 'catch-all'},
        ],
    }

    run(dd_run_check, instance)

    # Every firewall is contacted (only 192.0.2.10 answers); only the username/password entry logs in.
    assert {c.host for c in fake_panos.calls} == {'192.0.2.10', '198.51.100.7', '2001:db8::1'}
    assert [(c.host, c.params['user']) for c in fake_panos.calls if c.type == 'keygen'] == [('192.0.2.10', 'u')]


@pytest.mark.parametrize(
    'changes, message',
    [
        pytest.param({'firewalls': None}, 'One of `firewalls` or `panorama_host` is required', id='neither-mode'),
        pytest.param({'panorama_host': 'pan.example.com'}, 'not both', id='both-modes'),
        pytest.param({'firewalls': ['fw.example.com']}, '`fw.example.com` is not a valid IP', id='non-ip-entry'),
        pytest.param({'firewalls': ['192.0.2.10', '192.0.2.10']}, '`192.0.2.10` is duplicated', id='duplicate-ip'),
        pytest.param({'firewall_credentials': [{'username': 'u'}]}, 'entry 0 must set', id='credential-username-only'),
        pytest.param(
            {'firewall_credentials': [{'username': 'u', 'password': 'p', 'api_key': 'k'}]},
            'entry 0 must set',
            id='credential-both',
        ),
        pytest.param(
            {'firewall_credentials': [{'username': 'u', 'api_key': 'k'}]},
            'entry 0 must set',
            id='credential-key-and-username',
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
        pytest.param(
            {'security_rule_filter': ['^ok-', '[unclosed']},
            r'`security_rule_filter` entry `\[unclosed` is not a valid regular expression',
            id='bad-rule-filter-pattern',
        ),
    ],
)
def test_invalid_static_config(dd_run_check, changes, message):
    with pytest.raises(Exception, match=message):
        run(dd_run_check, instance_with(STATIC_INSTANCE, changes))


@pytest.mark.parametrize(
    'changes, message',
    [
        pytest.param({'panorama_api_key': None}, '`panorama_host` requires', id='no-auth'),
        pytest.param(
            {'panorama_username': 'u', 'panorama_password': 'p'}, '`panorama_host` requires', id='login-and-key'
        ),
        pytest.param({'firewall_ips': {'include': ['not-a-cidr']}}, 'firewall_ips.include', id='bad-include'),
    ],
)
def test_invalid_panorama_config(dd_run_check, changes, message):
    with pytest.raises(Exception, match=message):
        run(dd_run_check, instance_with(PANORAMA_INSTANCE, changes))
