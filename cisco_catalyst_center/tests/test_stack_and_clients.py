# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Switch stack and aggregate client health collectors."""

from __future__ import annotations

from contextlib import nullcontext as does_not_raise

import pytest

from datadog_checks.cisco_catalyst_center.collectors import collect_client_health, collect_stacks
from datadog_checks.cisco_catalyst_center.errors import CatalystApiError

from .common import client_from_script as _client
from .common import load_captured, metric_values, with_value

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


# -- stacks -----------------------------------------------------------------------


def test_collect_stacks_given_the_captured_stack_emits_member_count_and_state(aggregator, instance, check):
    # Cisco reports ACTIVE / STANDBY / MEMBER for the role, not the master/member the brief
    # describes. And stackPortInfo is null rather than an empty list -- iterating it raises
    # TypeError on the first real payload, which is what the prior design documents got wrong.
    stack = load_captured('intent_stack')

    collect_stacks(check, _client(instance, [stack, stack]), SWITCHES)

    # One lookup per switch, each tagged with its own device identity.
    aggregator.assert_metric('cisco_catalyst_center.device.stack.member.count', count=2)
    assert metric_values(aggregator, 'cisco_catalyst_center.device.stack.member.count', 'device_name:sw1') == [1]
    aggregator.assert_metric_has_tag(
        'cisco_catalyst_center.device.stack.member.count', 'device_id:default:10.10.20.175'
    )
    assert metric_values(
        aggregator,
        'cisco_catalyst_center.device.stack.member.state',
        'device_name:sw1',
        'stack_role:ACTIVE',
        'stack_member:1',
    ) == [1]
    aggregator.assert_metric('cisco_catalyst_center.device.stack.port.status', count=0)


def test_collect_stacks_given_populated_stack_ports_emits_status(aggregator, instance, check):
    stack = load_captured('intent_stack')
    stack = with_value(
        stack,
        'response.stackPortInfo',
        [{'name': 'StackPort1', 'isSynchOk': 'Yes', 'linkActive': True, 'neighborPort': 'StackPort2'}],
    )

    collect_stacks(check, _client(instance, [stack]), SWITCHES[:1])

    assert metric_values(aggregator, 'cisco_catalyst_center.device.stack.port.status', 'stack_port:StackPort1') == [1]


def test_collect_stacks_skips_devices_that_are_not_switches(instance, check):
    devices = [{'id': 'uuid-ap1', 'name': 'ap1', 'deviceFamily': 'Unified AP'}]
    client = _client(instance, [load_captured('intent_stack')])

    collect_stacks(check, client, devices)

    assert client.http.requests == [], 'stack is a per-device fan-out; only switches should be asked'


def test_collect_stacks_skips_switches_that_are_unreachable(instance, check):
    # Catalyst Center can only answer for an unreachable switch from its last-known copy, which
    # would report members that have lost power as ready. Skipping it also saves the request.
    devices = [SWITCHES[0], {**SWITCHES[1], 'reachabilityHealthStatus': 'UNREACHABLE'}]
    client = _client(instance, [load_captured('intent_stack')])

    collect_stacks(check, client, devices)

    assert not [request for request in client.http.requests if 'uuid-sw2' in request['url']]


FAILURE = {'status_code': 500, 'json': {}}


@pytest.mark.parametrize(
    ('script', 'expectation'),
    [
        pytest.param([FAILURE, load_captured('intent_stack')], does_not_raise(), id='one-switch-failing'),
        # Matching the message tells the aggregate error apart from one switch's error escaping.
        pytest.param(
            [FAILURE, FAILURE],
            pytest.raises(CatalystApiError, match='any of the 2 switches'),
            id='every-switch-failing',
        ),
    ],
)
def test_collect_stacks_given_failing_switches_raises_only_when_every_one_fails(instance, check, script, expectation):
    # One failing switch is skipped so it cannot cost the cycle. When every switch fails, nothing
    # was collected, and returning normally would report the cycle as a success.
    with expectation:
        collect_stacks(check, _client(instance, script), SWITCHES)


# -- aggregate client health ------------------------------------------------------


def test_collect_client_health_given_no_clients_counts_zero_and_skips_the_score(aggregator, instance, check):
    # The count is a real measurement even at zero. The score is not: scoreValue is -1 when
    # Catalyst Center has no client data, and emitting that graphs a false health.
    collect_client_health(check, _client(instance, [load_captured('intent_client_health_empty')]))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.count', 'client_type:ALL') == [0]
    aggregator.assert_metric('cisco_catalyst_center.client.health', count=0)


def test_collect_client_health_given_real_score_emits_it(aggregator, instance, check):
    payload = with_value(load_captured('intent_client_health_empty'), 'response.0.scoreDetail.0.scoreValue', 87)

    collect_client_health(check, _client(instance, [payload]))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.health', 'client_type:ALL') == [87]
