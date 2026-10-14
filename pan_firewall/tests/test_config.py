# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import re
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck

from .common import PANORAMA_INSTANCE, STATIC_INSTANCE


def run(dd_run_check, instance: dict[str, Any]) -> PanFirewallCheck:
    check = PanFirewallCheck('pan_firewall', {}, [instance])
    dd_run_check(check)
    return check


def instance_with(base, changes):
    """`base` with `changes` applied; a change to None removes the option."""
    instance = {**copy.deepcopy(base), **changes}
    return {k: v for k, v in instance.items() if v is not None}


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
    run(dd_run_check, instance_with(base, changes))


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


CONF_EXAMPLE = Path(__file__).parent.parent / 'datadog_checks' / 'pan_firewall' / 'data' / 'conf.yaml.example'
# The `instances/http` options the check hides: its own auth (`firewall_credentials`, `X-PAN-KEY`) replaces them.
HIDDEN_HTTP_OPTIONS = [
    'auth_type',
    'use_legacy_auth_encoding',
    'username',
    'password',
    'ntlm_domain',
    'kerberos_auth',
    'kerberos_cache',
    'kerberos_delegate',
    'kerberos_force_initiate',
    'kerberos_hostname',
    'kerberos_principal',
    'kerberos_keytab',
    'auth_token',
    'aws_region',
    'aws_host',
    'aws_service',
    'headers',
    'extra_headers',
]
VISIBLE_HTTP_OPTIONS = [
    'proxy',
    'skip_proxy',
    'timeout',
    'connect_timeout',
    'read_timeout',
    'persist_connections',
    'log_requests',
    'tls_verify',
    'tls_ca_cert',
    'tls_use_host_header',
    'tls_cert',
    'tls_private_key',
    'tls_protocols_allowed',
    'tls_ciphers',
    'allow_redirects',
    'request_size',
]


def test_example_config_hides_only_the_http_auth_and_header_options():
    documented = set(re.findall(r'^\s*## @param (\w+) ', CONF_EXAMPLE.read_text(), re.MULTILINE))

    assert documented & set(HIDDEN_HTTP_OPTIONS) == set()
    assert set(VISIBLE_HTTP_OPTIONS) - documented == set()


@pytest.mark.parametrize('base', [STATIC_INSTANCE, PANORAMA_INSTANCE], ids=['static', 'panorama'])
@pytest.mark.parametrize(
    'changes, expected', [({}, True), ({'persist_connections': False}, False)], ids=['default', 'turned-off']
)
def test_persist_connections_is_on_by_default_and_can_be_turned_off(dd_run_check, base, changes, expected):
    check = run(dd_run_check, {**copy.deepcopy(base), **changes})

    clients = [poller.client for poller in check._pollers.values()]
    if check.config.panorama_host:
        clients.append(check._source._client)
    assert clients and all(client._http is check.http for client in clients)
    assert check.http.persist_connections is expected


@pytest.mark.parametrize(
    'init_config, instance_timeout, expected',
    [({}, None, 30), ({'timeout': 7}, None, 7), ({'timeout': 7}, 12, 12)],
    ids=['default', 'init-config', 'instance-overrides-init-config'],
)
def test_timeout_comes_from_the_instance_then_init_config(init_config, instance_timeout, expected):
    check = PanFirewallCheck(
        'pan_firewall', init_config, [instance_with(STATIC_INSTANCE, {'timeout': instance_timeout})]
    )

    assert check.http.options['timeout'] == (expected, expected)
