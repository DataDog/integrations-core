# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.auth import Credentials
from datadog_checks.pan_firewall.config_models.instance import FirewallCredential, InstanceConfig
from datadog_checks.pan_firewall.firewalls import FirewallTarget, StaticFirewallSource, resolve_credentials

SUBNET = FirewallCredential(cidr='10.0.0.0/24', username='subnet', password='pw1')
OTHER = FirewallCredential(cidr='192.0.2.0/24', api_key='key2')
DEFAULT = FirewallCredential(username='default', password='pw3')


@pytest.mark.parametrize(
    'ip, entries, expected',
    [
        ('10.0.0.5', [OTHER, SUBNET, DEFAULT], Credentials('subnet', 'pw1', None)),
        ('192.0.2.7', [SUBNET, OTHER], Credentials(None, None, 'key2')),
        ('172.16.0.1', [SUBNET, DEFAULT], Credentials('default', 'pw3', None)),
        ('10.0.0.5', [DEFAULT, SUBNET], Credentials('default', 'pw3', None)),
        ('172.16.0.1', [SUBNET, OTHER], None),
    ],
    ids=['first-cidr-match', 'api-key-entry', 'no-cidr-matches-all', 'order-respected', 'no-match'],
)
def test_resolve_credentials(ip, entries, expected):
    assert resolve_credentials(ip, entries) == expected


def test_static_source_lists_targets_in_config_order():
    config = InstanceConfig.model_validate(
        {
            'firewalls': ['192.0.2.7', '10.0.0.5', '10.0.0.4'],
            'firewall_credentials': [SUBNET.model_dump(), OTHER.model_dump()],
        },
        context={'configured_fields': ['firewalls', 'firewall_credentials']},
    )

    assert StaticFirewallSource(config).list_firewalls() == [
        FirewallTarget('192.0.2.7', Credentials(None, None, 'key2')),
        FirewallTarget('10.0.0.5', Credentials('subnet', 'pw1', None)),
        FirewallTarget('10.0.0.4', Credentials('subnet', 'pw1', None)),
    ]
