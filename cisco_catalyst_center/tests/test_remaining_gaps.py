# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The unblocked items from the gap analysis.

Reachability signal, device-level throughput aggregate, uplink aggregate, L3 topology, top-N
applications, and the two NDM fields named in the brief's P0 metadata tables.
"""

from __future__ import annotations

import pytest

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import (
    collect_application_health,
    collect_devices,
    collect_interfaces,
    collect_l3_topology,
)
from datadog_checks.cisco_catalyst_center.ndm_models import create_interface_metadata

from .common import load_captured, metric_values, with_value
from .conftest import ScriptedHttp, ViewRoutedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


# -- reachability -----------------------------------------------------------------


@pytest.mark.parametrize(
    ('reachability', 'expected'),
    [
        ('REACHABLE', 1),
        ('UNREACHABLE', 0),
    ],
)
def test_collect_devices_maps_reachability_to_a_gauge(aggregator, instance, reachability, expected):
    # "Is this device up" was previously answerable only from NDM metadata, which is not
    # alertable. Now it is a metric.
    payload = with_value(load_captured('data_network_devices'), 'response.0.reachabilityHealthStatus', reachability)
    client = CatalystCenterClient(instance, http=ScriptedHttp([payload]))

    collect_devices(_check(instance), client, collect_wireless=False)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == [expected]


def test_collect_devices_tags_reachability_state(aggregator, instance):
    client = CatalystCenterClient(instance, http=ScriptedHttp([load_captured('data_network_devices')]))

    collect_devices(_check(instance), client, collect_wireless=False)

    aggregator.assert_metric_has_tag('cisco_catalyst_center.device.health', 'reachability:REACHABLE')


# -- device throughput and uplink aggregates --------------------------------------

VIEWS = {
    'configuration': load_captured('data_interfaces_configuration'),
    'statistics': load_captured('data_interfaces_statistics'),
}


def test_device_throughput_total_equals_the_sum_of_its_interfaces(aggregator, instance):
    # The brief asks for device-level rx/tx bps. Per-interface rates exist; this sums them per
    # device so the bullet is answerable without the caller doing arithmetic in a dashboard.
    # 10.10.20.176 reports three interfaces with a non-zero rxRate, totalling 733.0.
    client = CatalystCenterClient(instance, http=ViewRoutedHttp(VIEWS))

    collect_interfaces(_check(instance), client, views=('configuration', 'statistics'))

    assert metric_values(aggregator, 'cisco_catalyst_center.device.throughput.rx', 'device_ip:10.10.20.176') == [733.0]


def test_collect_interfaces_given_no_uplinks_emits_no_uplink_aggregate(aggregator, instance):
    # isWan is null on every sandbox interface, so there is no uplink subset to aggregate.
    client = CatalystCenterClient(instance, http=ViewRoutedHttp(VIEWS))

    collect_interfaces(_check(instance), client, views=('configuration', 'statistics'))

    aggregator.assert_metric('cisco_catalyst_center.device.uplink.throughput.rx', count=0)


def test_collect_interfaces_aggregates_uplink_throughput_when_iswan_is_set(aggregator, instance):
    config = with_value(load_captured('data_interfaces_configuration'), 'response.0.isWan', True)
    client = CatalystCenterClient(instance, http=ViewRoutedHttp(dict(VIEWS, configuration=config)))

    collect_interfaces(_check(instance), client, views=('configuration', 'statistics'))

    assert metric_values(aggregator, 'cisco_catalyst_center.device.uplink.count', 'device_ip:10.10.20.176') == [1]
    assert metric_values(aggregator, 'cisco_catalyst_center.device.uplink.throughput.rx', 'device_ip:10.10.20.176')


# -- L3 topology ------------------------------------------------------------------


def test_collect_l3_topology_emits_link_and_node_counts(aggregator, instance):
    client = CatalystCenterClient(instance, http=ScriptedHttp([load_captured('intent_topology_l3_ospf')]))

    collect_l3_topology(_check(instance), client, topology_type='ospf')

    assert metric_values(aggregator, 'cisco_catalyst_center.topology.l3.link.count', 'topology_type:ospf') == [10]
    assert metric_values(aggregator, 'cisco_catalyst_center.topology.l3.node.count', 'topology_type:ospf') == [4]


# -- top-N applications -----------------------------------------------------------

SITES = [{'id': 'site-a', 'siteHierarchy': 'Global/A'}]


def test_collect_application_health_sorts_by_usage_descending(aggregator, instance):
    # "Top applications by usage per site" is a sort, not a separate endpoint.
    client = CatalystCenterClient(instance, http=ScriptedHttp([load_captured('data_network_applications')]))

    collect_application_health(_check(instance), client, sites=SITES)

    params = client.http.requests[0]['params']
    assert params['sortBy'] == 'usage'
    assert params['order'] == 'des'


# -- NDM fields named in the brief ------------------------------------------------


def test_interface_metadata_port_role_prefers_uplink_when_iswan_is_set():
    # The brief derives port_role from interfaceType, portMode and description; an interface the
    # appliance has identified as a WAN link is an uplink regardless of its port mode.
    record = dict(load_captured('data_interfaces_configuration')['response'][0], isWan=True)

    assert create_interface_metadata(record, namespace='default').port_role == 'uplink'
