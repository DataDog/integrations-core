# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-client signal quality and onboarding, aggregated server-side.

The brief asks for RSSI/SNR "per client". Emitting a series per client would put client MAC in
the tag set, which at Pentair scale is tens of thousands of series for a metric nobody queries
per-device. Catalyst Center can do the aggregation itself, so this asks the appliance to group by
SSID and band and emits at that cardinality instead.

The sandbox has zero clients, so the appliance answers with ``null`` in every slot -- not empty
lists. That distinction is the main thing these tests pin.
"""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_client_experience

from .common import load_captured, metric_values, with_value
from .conftest import ScriptedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance, payload):
    return CatalystCenterClient(instance, http=ScriptedHttp([payload]))


EMPTY = 'data_clients_summary_analytics'


def test_collect_client_experience_asks_the_appliance_to_aggregate(instance):
    # The captured payload is the sandbox's zero-client answer, where `aggregateAttributes` and
    # `groups` are both null rather than []. Iterating either raises TypeError, so this run also
    # has to survive the request it makes coming back empty.
    client = _client(instance, load_captured(EMPTY))

    collect_client_experience(_check(instance), client, group_by=('ssid', 'band'))

    body = client.http.requests[0]['json']
    assert body['groupBy'] == ['ssid', 'band']
    requested = {(a['name'], a['function']) for a in body['aggregateAttributes']}
    assert ('rssi', 'avg') in requested
    assert ('avgRunDuration', 'avg') in requested


def test_collect_client_experience_emits_signal_quality_per_group(aggregator, instance):
    payload = with_value(
        load_captured(EMPTY),
        'response',
        {
            'attributes': None,
            'aggregateAttributes': None,
            'groups': [
                {
                    'attributes': [{'name': 'ssid', 'value': 'corp'}, {'name': 'band', 'value': '5GHZ'}],
                    'aggregateAttributes': [
                        {'name': 'rssi', 'function': 'avg', 'value': -58},
                        {'name': 'snr', 'function': 'avg', 'value': 34},
                    ],
                }
            ],
        },
    )

    collect_client_experience(_check(instance), _client(instance, payload))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.rssi.avg', 'ssid:corp', 'band:5GHZ') == [-58]
    assert metric_values(aggregator, 'cisco_catalyst_center.client.snr.avg', 'ssid:corp') == [34]
    # Server-side aggregation exists precisely to bound the tag set. Asserting the exact keys --
    # rather than only that client MAC is absent -- also catches a third dimension appearing.
    rssi = aggregator.metrics('cisco_catalyst_center.client.rssi.avg')[0]
    assert {tag.split(':', 1)[0] for tag in rssi.tags} == {'ssid', 'band'}


def test_collect_client_experience_emits_top_level_aggregates_and_skips_the_null_ones(aggregator, instance):
    # Onboarding durations arrive ungrouped, in the top-level `aggregateAttributes` slot. Any
    # one of them can come back with value null when the field has no data, and emitting that
    # as a zero would graph an instant onboarding that never happened.
    payload = with_value(
        load_captured(EMPTY),
        'response',
        {
            'attributes': None,
            'groups': None,
            'aggregateAttributes': [
                {'name': 'avgRunDuration', 'function': 'avg', 'value': 1500},
                {'name': 'avgDhcpDuration', 'function': 'avg', 'value': 250},
                {'name': 'rssi', 'function': 'avg', 'value': None},
            ],
        },
    )

    collect_client_experience(_check(instance), _client(instance, payload))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.onboarding.duration') == [1500]
    assert metric_values(aggregator, 'cisco_catalyst_center.client.onboarding.dhcp.duration') == [250]
    aggregator.assert_metric('cisco_catalyst_center.client.rssi.avg', count=0)
