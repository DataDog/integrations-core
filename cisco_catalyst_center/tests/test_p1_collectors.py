# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The five P1 domains from the product brief.

Topology, SD-Access Fabric, Assurance Issues, Application Visibility, Security.

Only topology has real data on the always-on sandbox. The other four return empty-but-real
responses, which is precisely why they make good fixtures: the collector must neither crash nor
invent a zero where the appliance reported nothing.

Issues emit both metrics and Datadog events, on the same reasoning that settled assurance
events: counts are what a monitor alerts on, the event body is what someone reads afterwards to
find out why. Security still emits metrics only.
"""

from __future__ import annotations

import pytest

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import (
    collect_application_health,
    collect_assurance_issues,
    collect_l3_topology,
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


def test_collect_topology_given_the_captured_graph_emits_a_count_and_a_status_per_link(aggregator, instance):
    collect_topology(_check(instance), _client(instance, [load_captured('intent_topology_physical')]))

    assert metric_values(aggregator, 'cisco_catalyst_center.topology.link.count') == [10]
    aggregator.assert_metric('cisco_catalyst_center.topology.link.status', count=10)


def test_collect_topology_given_a_down_link_reports_zero(aggregator, instance):
    payload = with_value(load_captured('intent_topology_physical'), 'response.links.0.linkStatus', 'down')

    collect_topology(_check(instance), _client(instance, [payload]))

    assert 0 in metric_values(aggregator, 'cisco_catalyst_center.topology.link.status')


def test_collect_l3_topology_emits_link_and_node_counts(aggregator, instance):
    collect_l3_topology(
        _check(instance), _client(instance, [load_captured('intent_topology_l3_ospf')]), topology_type='ospf'
    )

    assert metric_values(aggregator, 'cisco_catalyst_center.topology.l3.link.count', 'topology_type:ospf') == [10]
    assert metric_values(aggregator, 'cisco_catalyst_center.topology.l3.node.count', 'topology_type:ospf') == [4]


# -- SD-Access fabric -------------------------------------------------------------


@pytest.mark.parametrize(
    'devices',
    [
        pytest.param([], id='no-devices'),
        pytest.param([{'id': 'u1', 'name': 'sw1', 'fabricDetails': None}], id='no-fabric-role'),
    ],
)
def test_collect_sda_fabric_given_no_fabric_emits_nothing_and_does_not_raise(aggregator, instance, devices):
    # The sandbox has no fabric. Both summary endpoints answer 200 with an empty list, and every
    # device record carries a null fabricDetails -- neither is a zero to report.
    script = [
        load_captured('data_fabric_site_health_summaries'),
        load_captured('data_virtual_network_health_summaries'),
    ]

    collect_sda_fabric(_check(instance), _client(instance, script), devices=devices)

    aggregator.assert_metric('cisco_catalyst_center.fabric.site.health', count=0)
    aggregator.assert_metric('cisco_catalyst_center.fabric.device.count', count=0)


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


# Issues are stateful in a way assurance events are not: an open issue comes back on every cycle
# until it clears. `mostRecentOccurredTime` is the watermark that stops one open issue becoming
# one Datadog event per cycle for as long as it stays open.
OPEN_ISSUE = {
    'issueId': 'i1',
    'name': 'Switch unreachable',
    'severity': 'High',
    'priority': 'P1',
    'category': 'Connectivity',
    'status': 'active',
    'mostRecentOccurredTime': 1_755_002_000_000,
    'summary': 'Device did not respond to three consecutive polls',
    'suggestedActions': 'Check the uplink cable; verify PoE budget',
    'deviceType': 'Switches and Hubs',
}


def _issues(*records):
    return with_value(load_captured('data_assurance_issues'), 'response', list(records))


def test_collect_assurance_issues_submits_an_event_carrying_the_diagnosis(aggregator, instance):
    # The brief's separate issue-enrichment call is unnecessary because suggestedActions arrives
    # in this response -- but free text cannot ride on a metric tag, so it needs an event body.
    # Issue priority runs P1 (most severe) to P4, the inverse of the syslog severity scale the
    # assurance *event* collector reads. Mapping one with the other's table inverts every alert.
    collect_assurance_issues(_check(instance), _client(instance, [_issues(OPEN_ISSUE)]))

    assert 'Check the uplink cable; verify PoE budget' in aggregator.events[0]['msg_text']
    assert aggregator.events[0]['alert_type'] == 'error'


def test_collect_assurance_issues_given_an_issue_already_reported_counts_it_without_a_new_event(aggregator, instance):
    # Without the watermark, an issue that stays open produces one event every cycle, forever.
    # The counts are current state though, so it keeps counting on the cycles it is not re-reported.
    collect_assurance_issues(
        _check(instance),
        _client(instance, [_issues(OPEN_ISSUE)]),
        reported_through=OPEN_ISSUE['mostRecentOccurredTime'],
    )

    assert not aggregator.events
    assert metric_values(aggregator, 'cisco_catalyst_center.issue.total.count') == [1]


def test_collect_assurance_issues_returns_the_latest_occurrence_as_the_new_watermark(instance):
    # The caller stores this and hands it back next cycle. If it does not advance past the newest
    # issue, every issue is reported again on the following cycle.
    older = dict(OPEN_ISSUE, issueId='i0', mostRecentOccurredTime=1_755_001_000_000)

    watermark = collect_assurance_issues(_check(instance), _client(instance, [_issues(older, OPEN_ISSUE)]))

    assert watermark == 1_755_002_000_000


# -- application visibility -------------------------------------------------------

SITES = [{'id': 'site-a', 'siteHierarchy': 'Global/A'}]


def test_collect_application_health_asks_each_site_for_its_top_applications_by_usage(aggregator, instance):
    # networkApplications rejects a call without siteId (errorCode 14029). Note the API's own
    # message says "siteIds", but the accepted parameter is singular. "Top applications by usage
    # per site" is a sort on that same call rather than a separate endpoint.
    client = _client(instance, [load_captured('data_network_applications')])

    collect_application_health(_check(instance), client, sites=SITES)

    params = client.http.requests[0]['params']
    assert (params['siteId'], params['sortBy'], params['order']) == ('site-a', 'usage', 'des')
    # The captured page is empty, and an empty page is not a zero.
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


def test_collect_application_health_given_no_sites_makes_no_calls(instance):
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
