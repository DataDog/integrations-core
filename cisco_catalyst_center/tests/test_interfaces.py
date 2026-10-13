# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Interface collector tests.

The interfaces endpoint exposes four views -- `configuration`, `statistics`, `stackPort`
and `poE` -- and a view *replaces* the field set rather than extending it. So the collector
issues one paginated call per enabled view and joins them on the interface `id`.
"""

from __future__ import annotations

from typing import Any

import pytest

from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_interfaces

from .common import ViewRoutedHttp, load_captured, metric_values, with_value

# The intent API sweep is unconditional, so every collect_interfaces call issues it. It takes no
# `view` parameter, which is why it has to be routed by path.
INTENT_INTERFACE_PATH = '/dna/intent/api/v1/interface'

#: For tests whose subject is not the join. An appliance that returns no intent inventory is a
#: real answer, and it leaves the data API record untouched.
NO_INTENT: dict[str, Any] = {'response': []}


def _client(instance, by_view, intent=None):
    return CatalystCenterClient(
        instance,
        http=ViewRoutedHttp(
            by_view,
            by_path={INTENT_INTERFACE_PATH: intent if intent is not None else load_captured('intent_interface_global')},
        ),
    )


CONFIG_ONLY = {
    'configuration': load_captured('data_interfaces_configuration'),
    'statistics': load_captured('data_interfaces_statistics'),
}


# -- the request contract ---------------------------------------------------------------


@pytest.mark.parametrize('views', [('configuration',), ('configuration', 'statistics')])
def test_collect_interfaces_asks_for_each_view_then_sweeps_the_intent_api(instance, check, views):
    # A view replaces the field set rather than extending it, so an unasked-for view is a whole
    # extra paginated pass over every interface on the appliance. The viewless trailing call is
    # the intent sweep, which runs for everyone: it is the only source of `description`, and so
    # the only way an appliance that leaves `isWan` null can have an uplink identified at all.
    client = _client(instance, CONFIG_ONLY)

    collect_interfaces(check, client, views=views)

    assert [r['params'].get('view') for r in client.http.requests] == [*views, None]
    assert client.http.requests[-1]['url'].endswith(INTENT_INTERFACE_PATH)


# -- the configuration view -------------------------------------------------------------


def test_collect_interfaces_given_the_configuration_view_emits_status_and_speed_per_interface(
    aggregator, instance, check
):
    # One recorded page of 57 interfaces, and what the collector makes of it. `speed` is the
    # derived value: the API documents it in Kbps and returns it as a string, so a 1 GbE port
    # reporting "1000000" must land as 1_000_000_000. No sandbox interface sets isWan and none
    # is described as an uplink, so every port here is unclassified -- which earns no `uplink`
    # tag at all, rather than an `uplink:false` the data does not support.
    collect_interfaces(check, _client(instance, CONFIG_ONLY), views=('configuration',))

    aggregator.assert_metric('cisco_catalyst_center.interface.status', count=57)
    # `device_id` means the same thing here as on device metrics, so a port can be traced back to
    # its switch by one tag key.
    aggregator.assert_metric_has_tag('cisco_catalyst_center.interface.status', 'device_id:default:10.10.20.176')
    assert 1_000_000_000 in metric_values(aggregator, 'cisco_catalyst_center.interface.speed')
    uplink_tagged = [
        m
        for m in aggregator.metrics('cisco_catalyst_center.interface.status')
        if any(t.startswith('uplink:') for t in m.tags)
    ]
    assert uplink_tagged == []


@pytest.mark.parametrize('unusable_speed', [{}, 'auto'])
def test_collect_interfaces_given_unusable_speed_still_emits_the_other_interfaces(
    aggregator, instance, check, unusable_speed
):
    # `{}` is one of the four absent-data conventions emit.py documents, and `speed` is a string
    # field, so a non-numeric value is reachable. Either one must cost that single metric, not
    # abort the sweep and take every remaining interface's metrics with it.
    payload = with_value(load_captured('data_interfaces_configuration'), 'response.0.speed', unusable_speed)
    by_view = {**CONFIG_ONLY, 'configuration': payload}

    collect_interfaces(check, _client(instance, by_view), views=('configuration',))

    aggregator.assert_metric('cisco_catalyst_center.interface.status', count=57)


@pytest.mark.parametrize(('oper_status', 'expected'), [('UP', 1), ('Up', 1), ('DOWN', 0)])
def test_collect_interfaces_given_operstatus_case_variants_reports_status_correctly(
    aggregator, instance, check, oper_status, expected
):
    # The data API and the legacy endpoint disagree on case (`UP` vs `Up`), and a states set
    # missing one variant would silently read a healthy port as down rather than raising.
    config = with_value(load_captured('data_interfaces_configuration'), 'response.0.operStatus', oper_status)

    collect_interfaces(check, _client(instance, dict(CONFIG_ONLY, configuration=config)), views=('configuration',))

    # All four sandbox switches have a GigabitEthernet0/0; device_ip narrows to the one whose
    # record `with_value` actually modified.
    assert metric_values(
        aggregator, 'cisco_catalyst_center.interface.status', 'interface:GigabitEthernet0/0', 'device_ip:10.10.20.176'
    ) == [expected]


# -- the statistics view ----------------------------------------------------------------


def test_collect_interfaces_given_the_statistics_view_emits_throughput_per_interface(aggregator, instance, check):
    # Throughput must carry the same identity tags as configuration, or the two halves of a port
    # cannot be graphed together -- and every one of the four sandbox switches has a
    # GigabitEthernet0/0, so the device tag is what keeps them four series instead of one.
    collect_interfaces(check, _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    rx_rate = 'cisco_catalyst_center.interface.rx.rate'
    assert metric_values(aggregator, rx_rate, 'interface:GigabitEthernet0/0', 'device_ip:10.10.20.176') == [275.0]
    assert len(metric_values(aggregator, rx_rate, 'interface:GigabitEthernet0/0')) == 4
    aggregator.assert_metric_has_tags(rx_rate, ['interface:GigabitEthernet0/0', 'admin_status:UP'])
    # 0.0 is a real reading, not absent data. Skipping it hides the healthy baseline.
    aggregator.assert_metric('cisco_catalyst_center.interface.rx.error', value=0.0, at_least=1)


def test_collect_interfaces_given_the_statistics_view_totals_throughput_per_device(aggregator, instance, check):
    # The brief asks for device-level rx/tx bps. Per-interface rates exist; this sums them per
    # device so the bullet is answerable without the caller doing arithmetic in a dashboard.
    # 10.10.20.176 reports three interfaces with a non-zero rxRate, totalling 733.0. No sandbox
    # interface sets isWan or is described as an uplink, so there is no subset to aggregate.
    collect_interfaces(check, _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    assert metric_values(aggregator, 'cisco_catalyst_center.device.throughput.rx', 'device_ip:10.10.20.176') == [733.0]
    aggregator.assert_metric('cisco_catalyst_center.device.uplink.throughput.rx', count=0)


@pytest.mark.parametrize(
    ('is_wan', 'description', 'is_uplink'),
    [
        # `isWan` is the appliance's own judgement and wins in both directions, so a description
        # can neither promote a port it has ruled out nor demote one it has flagged.
        (True, 'access to printer', True),
        (False, 'uplink to core', False),
        # Null `isWan` is every interface the sandbox has ever returned. There the description is
        # the brief's fallback, matched case-insensitively.
        (None, 'Uplink to core', True),
        # A false positive silently inflates uplink throughput, which is worse than a dark
        # metric, so nothing short of the word itself counts.
        (None, 'access to printer', False),
        (None, None, False),
    ],
)
def test_collect_interfaces_aggregates_an_interface_as_an_uplink(
    aggregator, instance, check, is_wan, description, is_uplink
):
    config = with_value(load_captured('data_interfaces_configuration'), 'response.0.isWan', is_wan)
    config = with_value(config, 'response.0.description', description)

    collect_interfaces(
        check,
        # Empty intent inventory: the join would otherwise overwrite the description under test.
        _client(instance, dict(CONFIG_ONLY, configuration=config), intent=NO_INTENT),
        views=('configuration', 'statistics'),
    )

    assert metric_values(aggregator, 'cisco_catalyst_center.device.uplink.count', 'device_ip:10.10.20.176') == (
        [1] if is_uplink else []
    )
    tagged = metric_values(aggregator, 'cisco_catalyst_center.interface.status', 'uplink:true')
    assert bool(tagged) is is_uplink


def test_collect_interfaces_uplink_throughput_sums_only_the_uplink_subset(aggregator, instance, check):
    # The stated risk of the description fallback is a false positive silently inflating this
    # number, so it has to be the uplink's own rate and not the device's. 10.10.20.176 reports
    # 733.0 across three interfaces; GigabitEthernet0/0 -- response.0, the one flagged here --
    # reports 275.0 of it.
    config = with_value(load_captured('data_interfaces_configuration'), 'response.0.isWan', True)

    collect_interfaces(
        check,
        _client(instance, dict(CONFIG_ONLY, configuration=config)),
        views=('configuration', 'statistics'),
    )

    device_ip = 'device_ip:10.10.20.176'
    assert metric_values(aggregator, 'cisco_catalyst_center.device.uplink.throughput.rx', device_ip) == [275.0]
    assert metric_values(aggregator, 'cisco_catalyst_center.device.throughput.rx', device_ip) == [733.0]


# -- the PoE view -----------------------------------------------------------------------


def test_collect_interfaces_given_poe_view_with_null_fields_emits_no_poe_metrics(aggregator, instance, check):
    # Virtual switches return every PoE field null. The view still answers 200, so absence -- not
    # an HTTP error -- is how "no PoE hardware" is signalled.
    by_view = dict(CONFIG_ONLY, poE=load_captured('data_interfaces_poe'))

    collect_interfaces(check, _client(instance, by_view), views=('configuration', 'poE'))

    aggregator.assert_metric('cisco_catalyst_center.interface.poe.power_consumed', count=0)


def test_collect_interfaces_parses_watt_suffixed_poe_strings(aggregator, instance, check):
    # pdPowerConsumedInWatt is a string with the unit baked in, e.g. "10.5W".
    poe = with_value(load_captured('data_interfaces_poe'), 'response.0.pdPowerConsumedInWatt', '10.5W')
    by_view = dict(CONFIG_ONLY, poE=poe)

    collect_interfaces(check, _client(instance, by_view), views=('configuration', 'poE'))

    assert metric_values(aggregator, 'cisco_catalyst_center.interface.poe.power_consumed') == [10.5]


# -- intent API enrichment --------------------------------------------------------------

# The data API's configuration view returns `macAddress` and `description` as null on every
# interface, and the product brief specifies the intent API as the source for both. The intent
# API's global interface endpoint returns them in bulk, keyed by the same interface UUIDs.

# GigabitEthernet1/0/2 exercises all three cases at once: the data API leaves its macAddress
# null, the intent record's `name` is empty (it uses `portName`), and the two APIs disagree
# about its VLAN -- data says 101, intent says 1.
JOINED_INTERFACE = 'GigabitEthernet1/0/2'


def test_collect_interfaces_given_enrichment_fills_null_fields_without_overwriting_the_data_api(
    aggregator, instance, check
):
    # The intent record carries an empty `name` and puts the port in `portName`, and the two APIs
    # disagree on trunk ports: the data API reports the configured access VLAN, intent reports 1.
    # So the join fills what the data API left null and keeps the data API authoritative for the
    # rest -- copying intent's fields wholesale would blank the interface tag on every match.
    merged = collect_interfaces(check, _client(instance, CONFIG_ONLY), views=('configuration',))

    record = next(r for r in merged.values() if r.get('name') == JOINED_INTERFACE)
    assert record['macAddress'] == '52:54:00:07:29:d2'
    status = 'cisco_catalyst_center.interface.status'
    assert metric_values(aggregator, status, f'interface:{JOINED_INTERFACE}', 'vlan:101')
    # The intent inventory omits the 8 stack sub-interfaces the data API returns. They have no
    # metadata to gain, but they must not be dropped from the metrics either.
    aggregator.assert_metric(status, count=57)
