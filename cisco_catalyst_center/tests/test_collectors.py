# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Device collector tests.

The switch cases run against verbatim sandbox recordings. The access point and controller cases
run against a synthetic payload whose keys come from Cisco's schema and whose values were chosen
by hand -- see `tests/fixtures/wireless_synthetic/GENERATOR.py`. Assert on structure and
plumbing there, never on a value being realistic.
"""

from __future__ import annotations

import pytest

from datadog_checks.cisco_catalyst_center.collectors import collect_devices

from .common import client_from_payload as _client
from .common import load_captured, load_captured_reservable, load_wireless_synthetic, metric_values, with_value

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


@pytest.mark.parametrize(
    ('field', 'sentinel', 'metric'),
    [
        pytest.param('cpuScore', -1, 'cisco_catalyst_center.device.cpu.score', id='no-data'),
        # What the reservable sandbox scored a powered-off switch, recorded 2026-10-05.
        pytest.param('overallHealthScore', -2, 'cisco_catalyst_center.device.health', id='unreachable'),
    ],
)
def test_collect_devices_given_a_negative_sentinel_score_skips_that_metric(
    aggregator, instance, check, field, sentinel, metric
):
    # Scores run from 1 to 10, and Catalyst Center encodes "no data" as -1 and "unreachable" as
    # -2. Emitting either graphs a false value, and -2 drags any average below the poor band.
    payload = with_value(load_captured('data_network_devices'), f'response.0.metricsDetails.{field}', sentinel)

    collect_devices(check, _client(instance, payload), collect_wireless=False)

    aggregator.assert_metric(metric, count=3)


def test_collect_devices_given_an_unreachable_device_reports_only_its_reachability(aggregator, instance, check):
    # Catalyst Center keeps serving an unreachable device's last readings: the recorded sw4 was
    # powered off, yet its uptime kept counting and it still reported a wired client. Emitting
    # them would graph a switch that is up and serving clients.
    payload = load_captured_reservable('data_network_devices_switch_unreachable')

    collect_devices(check, _client(instance, payload), collect_wireless=False)

    reported = {name for name in aggregator.metric_names if metric_values(aggregator, name, 'device_name:sw4')}
    assert reported == {'cisco_catalyst_center.device.reachable'}


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
