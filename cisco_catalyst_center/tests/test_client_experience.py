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


def test_collect_client_experience_given_no_clients_does_not_raise(aggregator, instance):
    # `aggregateAttributes` and `groups` are both null, not []. Iterating either raises TypeError.
    collect_client_experience(_check(instance), _client(instance, load_captured(EMPTY)))

    aggregator.assert_metric('cisco_catalyst_center.client.rssi.avg', count=0)


def test_collect_client_experience_asks_the_appliance_to_aggregate(aggregator, instance):
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


def test_collect_client_experience_emits_onboarding_durations(aggregator, instance):
    payload = with_value(
        load_captured(EMPTY),
        'response',
        {
            'attributes': None,
            'groups': None,
            'aggregateAttributes': [
                {'name': 'avgRunDuration', 'function': 'avg', 'value': 1500},
                {'name': 'avgDhcpDuration', 'function': 'avg', 'value': 250},
            ],
        },
    )

    collect_client_experience(_check(instance), _client(instance, payload))

    assert metric_values(aggregator, 'cisco_catalyst_center.client.onboarding.duration') == [1500]
    assert metric_values(aggregator, 'cisco_catalyst_center.client.onboarding.dhcp.duration') == [250]


def test_collect_client_experience_does_not_tag_by_client_mac(aggregator, instance):
    # Aggregating server-side exists precisely to keep client MAC out of the tag set.
    payload = with_value(
        load_captured(EMPTY),
        'response',
        {
            'attributes': None,
            'groups': None,
            'aggregateAttributes': [{'name': 'rssi', 'function': 'avg', 'value': -60}],
        },
    )

    collect_client_experience(_check(instance), _client(instance, payload))

    for metric in aggregator.metrics('cisco_catalyst_center.client.rssi.avg'):
        assert not any(t.startswith(('client_mac:', 'mac_address:')) for t in metric.tags)


def test_collect_client_experience_given_a_null_aggregate_value_skips_it(aggregator, instance):
    # A requested aggregate can come back with value null when the field has no data.
    payload = with_value(
        load_captured(EMPTY),
        'response',
        {
            'attributes': None,
            'groups': None,
            'aggregateAttributes': [
                {'name': 'rssi', 'function': 'avg', 'value': None},
                {'name': 'snr', 'function': 'avg', 'value': 30},
            ],
        },
    )

    collect_client_experience(_check(instance), _client(instance, payload))

    aggregator.assert_metric('cisco_catalyst_center.client.rssi.avg', count=0)
    aggregator.assert_metric('cisco_catalyst_center.client.snr.avg', count=1)
