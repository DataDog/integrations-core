# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Switch stack and aggregate client health collectors."""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_client_health, collect_stacks

from .common import load_captured, metric_values, with_value
from .conftest import ScriptedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance, script):
    return CatalystCenterClient(instance, http=ScriptedHttp(script))


SWITCHES = [
    {
        'id': 'uuid-sw1',
        'name': 'sw1',
        'managementIpAddress': '10.10.20.175',
        'deviceFamily': 'Switches and Hubs',
    },
    {
        'id': 'uuid-sw2',
        'name': 'sw2',
        'managementIpAddress': '10.10.20.176',
        'deviceFamily': 'Switches and Hubs',
    },
]


def test_collect_stacks_tags_metrics_with_the_snmp_compatible_device_id(aggregator, instance):
    # Stack metrics hang off a device, so they carry the same device identity as the rest.
    collect_stacks(_check(instance), _client(instance, [load_captured('intent_stack')]), SWITCHES[:1])

    aggregator.assert_metric_has_tag(
        'cisco_catalyst_center.device.stack.member.count', 'device_id:default:10.10.20.175'
    )


# -- stacks -----------------------------------------------------------------------


def test_collect_stacks_emits_member_count_per_switch(aggregator, instance):
    stack = load_captured('intent_stack')

    collect_stacks(_check(instance), _client(instance, [stack, stack]), SWITCHES)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.stack.member.count', 'device_name:sw1') == [1]


def test_collect_stacks_emits_member_state_tagged_by_role(aggregator, instance):
    # Cisco reports ACTIVE / STANDBY / MEMBER here, not the master/member the brief describes.
    collect_stacks(_check(instance), _client(instance, [load_captured('intent_stack')]), SWITCHES[:1])

    assert metric_values(
        aggregator, 'cisco_catalyst_center.device.stack.member.state', 'stack_role:ACTIVE', 'stack_member:1'
    ) == [1]


def test_collect_stacks_given_null_stack_port_info_does_not_raise(aggregator, instance):
    # stackPortInfo is null, not an empty list. Iterating it raises TypeError on the first real
    # payload, which is what the prior design documents got wrong.
    collect_stacks(_check(instance), _client(instance, [load_captured('intent_stack')]), SWITCHES[:1])

    aggregator.assert_metric('cisco_catalyst_center.device.stack.port.status', count=0)


def test_collect_stacks_given_populated_stack_ports_emits_status(aggregator, instance):
    stack = load_captured('intent_stack')
    stack = with_value(
        stack,
        'response.stackPortInfo',
        [{'name': 'StackPort1', 'isSynchOk': 'Yes', 'linkActive': True, 'neighborPort': 'StackPort2'}],
    )

    collect_stacks(_check(instance), _client(instance, [stack]), SWITCHES[:1])

    assert metric_values(aggregator, 'cisco_catalyst_center.device.stack.port.status', 'stack_port:StackPort1') == [1]


def test_collect_stacks_skips_devices_that_are_not_switches(aggregator, instance):
    devices = [{'id': 'uuid-ap1', 'name': 'ap1', 'deviceFamily': 'Unified AP'}]
    client = _client(instance, [load_captured('intent_stack')])

    collect_stacks(_check(instance), client, devices)

    assert client.http.requests == [], 'stack is a per-device fan-out; only switches should be asked'


# -- aggregate client health ------------------------------------------------------


def test_collect_client_health_emits_counts_by_client_type(aggregator, instance):
    collect_client_health(_check(instance), _client(instance, [load_captured('intent_client_health_empty')]))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.count', 'client_type:ALL') == [0]


def test_collect_client_health_skips_the_minus_one_score(aggregator, instance):
    # scoreValue is -1 when Catalyst Center has no client data. Emitting it graphs a false health.
    collect_client_health(_check(instance), _client(instance, [load_captured('intent_client_health_empty')]))

    aggregator.assert_metric('cisco_catalyst_center.client.health', count=0)


def test_collect_client_health_given_real_score_emits_it(aggregator, instance):
    payload = with_value(load_captured('intent_client_health_empty'), 'response.0.scoreDetail.0.scoreValue', 87)

    collect_client_health(_check(instance), _client(instance, [payload]))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.health', 'client_type:ALL') == [87]
