# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The five P1 domains from the product brief.

Topology, SD-Access Fabric, Assurance Issues, Application Visibility, Security.

Only topology has real data on the always-on sandbox. The other four return empty-but-real
responses, which is precisely why they make good fixtures: the collector must neither crash nor
invent a zero where the appliance reported nothing.

Issues and security emit *metrics* here. Turning them into Datadog events is the separate
ingestion decision the brief leaves open, and it is not settled by this work.
"""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import (
    collect_application_health,
    collect_assurance_issues,
    collect_sda_fabric,
    collect_security,
    collect_topology,
)

from .common import load_captured, metric_values, with_value
from .conftest import ScriptedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance, script):
    return CatalystCenterClient(instance, http=ScriptedHttp(script))


# -- topology ---------------------------------------------------------------------


def test_collect_topology_emits_a_link_count(aggregator, instance):
    physical = load_captured('intent_topology_physical')

    collect_topology(_check(instance), _client(instance, [physical]))

    assert metric_values(aggregator, 'cisco_catalyst_center.topology.link.count') == [10]


def test_collect_topology_emits_link_status_per_link(aggregator, instance):
    collect_topology(_check(instance), _client(instance, [load_captured('intent_topology_physical')]))

    aggregator.assert_metric('cisco_catalyst_center.topology.link.status', count=10)


def test_collect_topology_given_a_down_link_reports_zero(aggregator, instance):
    payload = with_value(load_captured('intent_topology_physical'), 'response.links.0.linkStatus', 'down')

    collect_topology(_check(instance), _client(instance, [payload]))

    assert 0 in metric_values(aggregator, 'cisco_catalyst_center.topology.link.status')


def test_topology_links_reference_devices_by_the_same_uuid_used_for_ndm(aggregator, instance):
    # source/target are device UUIDs, which is what DeviceMetadata.id is now keyed on, so links
    # resolve to devices without a translation step.
    physical = load_captured('intent_topology_physical')
    device_ids = {d['id'] for d in load_captured('data_network_devices')['response']}

    endpoints = {link['source'] for link in physical['response']['links']}
    assert endpoints <= device_ids


# -- SD-Access fabric -------------------------------------------------------------


def test_collect_sda_fabric_given_no_fabric_emits_nothing_and_does_not_raise(aggregator, instance):
    # The sandbox has no fabric. Both summary endpoints answer 200 with an empty list.
    script = [
        load_captured('data_fabric_site_health_summaries'),
        load_captured('data_virtual_network_health_summaries'),
    ]

    collect_sda_fabric(_check(instance), _client(instance, script), devices=[])

    aggregator.assert_metric('cisco_catalyst_center.fabric.site.health', count=0)


def test_collect_sda_fabric_emits_device_role_counts_from_the_bulk_record(aggregator, instance):
    # The brief routes this through sda/edge-device and sda/border-device, which return 400 with
    # no list mode. fabricDetails on the device record carries the same information.
    devices = [
        {'id': 'u1', 'name': 'edge1', 'fabricDetails': {'fabricRole': ['edge'], 'fabricSiteName': 'campus'}},
        {'id': 'u2', 'name': 'brd1', 'fabricDetails': {'fabricRole': ['Border', 'edge'], 'fabricSiteName': 'campus'}},
    ]
    script = [
        load_captured('data_fabric_site_health_summaries'),
        load_captured('data_virtual_network_health_summaries'),
    ]

    collect_sda_fabric(_check(instance), _client(instance, script), devices=devices)

    assert metric_values(aggregator, 'cisco_catalyst_center.fabric.device.count', 'fabric_role:edge') == [2]
    assert metric_values(aggregator, 'cisco_catalyst_center.fabric.device.count', 'fabric_role:border') == [1]


def test_collect_sda_fabric_ignores_devices_with_no_fabric_role(aggregator, instance):
    devices = [{'id': 'u1', 'name': 'sw1', 'fabricDetails': None}]
    script = [
        load_captured('data_fabric_site_health_summaries'),
        load_captured('data_virtual_network_health_summaries'),
    ]

    collect_sda_fabric(_check(instance), _client(instance, script), devices=devices)

    aggregator.assert_metric('cisco_catalyst_center.fabric.device.count', count=0)


# -- assurance issues -------------------------------------------------------------


def test_collect_assurance_issues_given_none_open_emits_a_total_of_zero(aggregator, instance):
    # Zero open issues is a real measurement and the most common healthy state.
    collect_assurance_issues(_check(instance), _client(instance, [load_captured('data_assurance_issues')]))

    assert metric_values(aggregator, 'cisco_catalyst_center.issue.total.count') == [0]


def test_collect_assurance_issues_counts_by_severity_and_category(aggregator, instance):
    payload = with_value(
        load_captured('data_assurance_issues'),
        'response',
        [
            {'issueId': 'i1', 'severity': 'High', 'priority': 'P1', 'category': 'Connectivity', 'status': 'active'},
            {'issueId': 'i2', 'severity': 'High', 'priority': 'P2', 'category': 'Connectivity', 'status': 'active'},
            {'issueId': 'i3', 'severity': 'Low', 'priority': 'P4', 'category': 'Device', 'status': 'active'},
        ],
    )

    collect_assurance_issues(_check(instance), _client(instance, [payload]))

    assert metric_values(aggregator, 'cisco_catalyst_center.issue.count', 'severity:High') == [2]
    assert metric_values(aggregator, 'cisco_catalyst_center.issue.count', 'category:Device') == [1]


# -- application visibility -------------------------------------------------------

SITES = [{'id': 'site-a', 'siteHierarchy': 'Global/A'}]


def test_collect_application_health_requires_a_site_id_per_call(aggregator, instance):
    # networkApplications rejects a call without siteId (errorCode 14029). Note the API's own
    # message says "siteIds", but the accepted parameter is singular.
    client = _client(instance, [load_captured('data_network_applications')])

    collect_application_health(_check(instance), client, sites=SITES)

    assert client.http.requests[0]['params']['siteId'] == 'site-a'


def test_collect_application_health_given_no_applications_emits_nothing(aggregator, instance):
    collect_application_health(
        _check(instance), _client(instance, [load_captured('data_network_applications')]), sites=SITES
    )

    aggregator.assert_metric('cisco_catalyst_center.application.health', count=0)


def test_collect_application_health_emits_per_application_metrics(aggregator, instance):
    payload = with_value(
        load_captured('data_network_applications'),
        'response',
        [{'name': 'webex', 'healthScore': 8, 'usage': 4096, 'throughput': 512.0, 'packetLossPercent': 0.5}],
    )

    collect_application_health(_check(instance), _client(instance, [payload]), sites=SITES)

    assert metric_values(aggregator, 'cisco_catalyst_center.application.health', 'application:webex') == [8]
    assert metric_values(aggregator, 'cisco_catalyst_center.application.usage', 'application:webex') == [4096]


def test_collect_application_health_given_no_sites_makes_no_calls(aggregator, instance):
    client = _client(instance, [load_captured('data_network_applications')])

    collect_application_health(_check(instance), client, sites=[])

    assert client.http.requests == []


# -- security ---------------------------------------------------------------------


def test_collect_security_given_no_threats_emits_zero_counts(aggregator, instance):
    script = [load_captured('intent_security_rogue_empty'), load_captured('intent_security_threats_empty')]

    collect_security(_check(instance), _client(instance, script))

    assert metric_values(aggregator, 'cisco_catalyst_center.security.rogue.count') == [0]
    assert metric_values(aggregator, 'cisco_catalyst_center.security.threat.count') == [0]


def test_collect_security_counts_rogues_by_threat_level(aggregator, instance):
    rogues = with_value(
        load_captured('intent_security_rogue_empty'),
        'response',
        [
            {'threatLevel': 'High', 'macAddress': 'aa:bb', 'ssid': 'evil'},
            {'threatLevel': 'High', 'macAddress': 'cc:dd'},
        ],
    )
    script = [rogues, load_captured('intent_security_threats_empty')]

    collect_security(_check(instance), _client(instance, script))

    assert metric_values(aggregator, 'cisco_catalyst_center.security.rogue.count', 'threat_level:High') == [2]
