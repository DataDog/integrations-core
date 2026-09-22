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

import pytest

from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_devices

from .common import load_captured, load_wireless_synthetic, metric_values, with_value
from .conftest import ScriptedHttp


def _client(instance, payload):
    return CatalystCenterClient(instance, http=ScriptedHttp([payload]))


# -- switches, from the sandbox recording -----------------------------------------


def test_collect_devices_given_captured_switches_emits_the_expected_device_series(aggregator, instance, check):
    # Four recorded switches, and what the collector makes of them. `device_id` must mean one
    # thing across the whole integration: the {namespace}:{ip} form the SNMP check also uses,
    # with the Catalyst Center UUID travelling separately as `device_uuid`. An empty
    # errorInterfaces list means zero interfaces in error, which is a real datapoint -- skipping
    # it leaves a gap in the graph during healthy periods and a spike during unhealthy ones.
    collect_devices(check, _client(instance, load_captured('data_network_devices')), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=4)
    assert metric_values(aggregator, 'cisco_catalyst_center.device.health', 'device_name:sw1') == [10]
    aggregator.assert_metric_has_tags(
        'cisco_catalyst_center.device.health',
        ['device_id:default:10.10.20.175', 'device_uuid:aa754801-8895-41e8-8ca5-27ee415c9c42'],
    )
    aggregator.assert_metric_has_tag('cisco_catalyst_center.device.health', 'reachability:REACHABLE')
    aggregator.assert_metric('cisco_catalyst_center.device.link.error.count', value=0, count=4)
    assert metric_values(aggregator, 'cisco_catalyst_center.device.uptime', 'device_name:sw1') == [16847210]


@pytest.mark.parametrize(('reachability', 'expected'), [('REACHABLE', 1), ('UNREACHABLE', 0)])
def test_collect_devices_maps_reachability_to_a_gauge(aggregator, instance, check, reachability, expected):
    # "Is this device up" is answerable from NDM metadata, which is not alertable. The gauge is.
    payload = with_value(load_captured('data_network_devices'), 'response.0.reachabilityHealthStatus', reachability)

    collect_devices(check, _client(instance, payload), collect_wireless=False)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == [expected]


def test_collect_devices_given_score_of_minus_one_skips_that_metric(aggregator, instance, check):
    # -1 is Catalyst Center's "no data" sentinel for scores. Emitting it graphs a false value.
    payload = with_value(load_captured('data_network_devices'), 'response.0.metricsDetails.cpuScore', -1)

    collect_devices(check, _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.cpu.score', count=3)


# -- access points and controllers, from the synthetic payload --------------------


def test_collect_devices_given_wireless_records_emits_radio_and_controller_metrics(aggregator, instance, check):
    payload = load_wireless_synthetic('data_network_devices_wireless')

    collect_devices(check, _client(instance, payload), collect_wireless=True)

    noise = 'cisco_catalyst_center.device.ap.radio.noise'
    assert metric_values(aggregator, noise, 'radio_band:2.4Ghz') == [-92]
    assert metric_values(aggregator, noise, 'radio_band:5Ghz') == [-97]
    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.client.count', count=2)
    assert metric_values(aggregator, 'cisco_catalyst_center.device.ap.count', 'device_family:Wireless Controller') == [
        31
    ]


def test_collect_devices_given_wireless_disabled_emits_no_radio_metrics(aggregator, instance, check):
    payload = load_wireless_synthetic('data_network_devices_wireless')

    collect_devices(check, _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.noise', count=0)
    # The device-level metrics still land; only the radio fan-out is gated.
    aggregator.assert_metric('cisco_catalyst_center.device.health', count=2)


def test_collect_devices_given_null_ap_details_does_not_raise(aggregator, instance, check):
    # apDetails is null on every switch, and on controllers. `for r in record['apDetails']['radios']`
    # would raise TypeError on the first real payload.
    payload = load_captured('data_network_devices')

    collect_devices(check, _client(instance, payload), collect_wireless=True)

    aggregator.assert_metric('cisco_catalyst_center.device.ap.radio.noise', count=0)
