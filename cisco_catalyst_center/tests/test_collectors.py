# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Device collector tests.

The switch cases run against verbatim sandbox recordings. The access point and controller cases
run against a synthetic payload whose keys come from Cisco's schema and whose values were chosen
by hand -- see ``tests/fixtures/wireless_synthetic/GENERATOR.py``. Assert on structure and
plumbing there, never on a value being realistic.
"""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_devices

from .common import load_captured, load_wireless_synthetic, metric_values, with_value
from .conftest import ScriptedHttp


def _client(instance, payload):
    return CatalystCenterClient(instance, http=ScriptedHttp([payload]))


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def test_collect_devices_tags_metrics_with_the_snmp_compatible_device_id(aggregator, instance):
    # `device_id` must mean one thing across the whole integration: the {namespace}:{ip} form the
    # SNMP check also uses. The Catalyst Center UUID travels separately as `device_uuid`.
    collect_devices(_check(instance), _client(instance, load_captured('data_network_devices')), collect_wireless=False)

    aggregator.assert_metric_has_tag('cisco_catalyst_center.device.health', 'device_id:default:10.10.20.175')


def test_collect_devices_tags_metrics_with_the_catalyst_center_uuid(aggregator, instance):
    payload = load_captured('data_network_devices')
    uuid = payload['response'][0]['id']

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric_has_tag('cisco_catalyst_center.device.health', f'device_uuid:{uuid}')


def test_collect_devices_given_captured_switches_emits_health_per_device(aggregator, instance):
    collect_devices(_check(instance), _client(instance, load_captured('data_network_devices')), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=4)
    assert metric_values(aggregator, 'cisco_catalyst_center.device.health', 'device_name:sw1') == [10]


def test_collect_devices_given_score_of_minus_one_skips_that_metric(aggregator, instance):
    # -1 is Catalyst Center's "no data" sentinel for scores. Emitting it graphs a false value.
    payload = with_value(load_captured('data_network_devices'), 'response.0.metricsDetails.cpuScore', -1)

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.cpu.score', count=3)


def test_collect_devices_given_empty_error_interfaces_emits_count_of_zero(aggregator, instance):
    # [] means zero interfaces in error, which is a real datapoint. Skipping it leaves a gap in
    # the graph during healthy periods and a spike during unhealthy ones.
    collect_devices(_check(instance), _client(instance, load_captured('data_network_devices')), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.link.error.count', value=0, count=4)


def test_collect_devices_given_ap_record_emits_radio_metrics_tagged_by_band(aggregator, instance):
    payload = load_wireless_synthetic('data_network_devices_wireless')

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=True)

    noise = 'cisco_catalyst_center.device.ap.radio.noise'
    assert metric_values(aggregator, noise, 'radio_band:2.4Ghz') == [-92]
    assert metric_values(aggregator, noise, 'radio_band:5Ghz') == [-97]
    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.client.count', count=2)


def test_collect_devices_given_wireless_disabled_emits_no_radio_metrics(aggregator, instance):
    payload = load_wireless_synthetic('data_network_devices_wireless')

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.noise', count=0)
    # The device-level metrics still land; only the radio fan-out is gated.
    aggregator.assert_metric('cisco_catalyst_center.device.health', count=2)


def test_collect_devices_given_wlc_record_emits_ap_count(aggregator, instance):
    payload = load_wireless_synthetic('data_network_devices_wireless')

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=True)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.ap.count', 'device_family:Wireless Controller') == [
        31
    ]


def test_collect_devices_given_null_ap_details_does_not_raise(aggregator, instance):
    # apDetails is null on every switch, and on controllers. `for r in record['apDetails']['radios']`
    # would raise TypeError on the first real payload.
    payload = load_captured('data_network_devices')

    collect_devices(_check(instance), _client(instance, payload), collect_wireless=True)

    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.noise', count=0)


def test_collect_devices_given_string_numeric_uptime_emits_numeric(aggregator, instance):
    collect_devices(_check(instance), _client(instance, load_captured('data_network_devices')), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.uptime', count=4)
