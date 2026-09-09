# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Interface collector tests.

The interfaces endpoint exposes four views -- ``configuration``, ``statistics``, ``stackPort``
and ``poE`` -- and a view *replaces* the field set rather than extending it. So the collector
issues one paginated call per enabled view and joins them on the interface ``id``.
"""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_interfaces

from .common import load_captured, metric_values, with_value
from .conftest import ViewRoutedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance, by_view):
    return CatalystCenterClient(instance, http=ViewRoutedHttp(by_view))


CONFIG_ONLY = {
    'configuration': load_captured('data_interfaces_configuration'),
    'statistics': load_captured('data_interfaces_statistics'),
}


def test_collect_interfaces_tags_metrics_with_the_snmp_compatible_device_id(aggregator, instance):
    # Same meaning as on device metrics, so a port can be traced to its switch by one tag key.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration',))

    aggregator.assert_metric_has_tag('cisco_catalyst_center.interface.status', 'device_id:default:10.10.20.176')


def test_collect_interfaces_given_captured_config_emits_status_per_interface(aggregator, instance):
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration',))

    aggregator.assert_metric('cisco_catalyst_center.interface.status', count=57)


def test_collect_interfaces_converts_speed_from_kbps_to_bps(aggregator, instance):
    # The API documents `speed` in Kbps and returns it as a string. NDM and the metric are bps,
    # so a 1 GbE port reporting "1000000" must land as 1_000_000_000.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration',))

    assert 1_000_000_000 in metric_values(aggregator, 'cisco_catalyst_center.interface.speed')


def test_collect_interfaces_given_statistics_view_emits_throughput(aggregator, instance):
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    assert metric_values(
        aggregator,
        'cisco_catalyst_center.interface.rx.rate',
        'interface:GigabitEthernet0/0',
        'device_ip:10.10.20.176',
    ) == [275.0]


def test_collect_interfaces_distinguishes_same_named_ports_on_different_devices(aggregator, instance):
    # Every one of the four sandbox switches has a GigabitEthernet0/0. Interface name alone is
    # not an identity, so the device tag is what keeps them four series instead of one.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    same_name = metric_values(aggregator, 'cisco_catalyst_center.interface.rx.rate', 'interface:GigabitEthernet0/0')
    assert len(same_name) == 4


def test_collect_interfaces_given_statistics_view_emits_zero_errors(aggregator, instance):
    # 0.0 is a real reading, not absent data. Skipping it hides the healthy baseline.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    aggregator.assert_metric('cisco_catalyst_center.interface.rx.error', value=0.0, at_least=1)


def test_collect_interfaces_joins_views_onto_one_series(aggregator, instance):
    # Throughput must carry the same identity tags as configuration, or the two halves of a port
    # cannot be graphed together.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration', 'statistics'))

    aggregator.assert_metric_has_tags(
        'cisco_catalyst_center.interface.rx.rate', ['interface:GigabitEthernet0/0', 'admin_status:UP']
    )


def test_collect_interfaces_given_statistics_disabled_makes_one_call(aggregator, instance):
    client = _client(instance, CONFIG_ONLY)

    collect_interfaces(_check(instance), client, views=('configuration',))

    assert [r['params']['view'] for r in client.http.requests] == ['configuration']


def test_collect_interfaces_given_null_iswan_omits_the_uplink_tag(aggregator, instance):
    # isWan is null on every sandbox interface. A tag of `uplink:None` would be worse than none.
    collect_interfaces(_check(instance), _client(instance, CONFIG_ONLY), views=('configuration',))

    tagged = [
        m
        for m in aggregator.metrics('cisco_catalyst_center.interface.status')
        if any(t.startswith('uplink:') for t in m.tags)
    ]
    assert tagged == []


def test_collect_interfaces_given_iswan_true_tags_the_uplink(aggregator, instance):
    payload = with_value(load_captured('data_interfaces_configuration'), 'response.0.isWan', True)
    by_view = {'configuration': payload, 'statistics': load_captured('data_interfaces_statistics')}

    collect_interfaces(_check(instance), _client(instance, by_view), views=('configuration',))

    assert metric_values(aggregator, 'cisco_catalyst_center.interface.status', 'uplink:true')


def test_collect_interfaces_given_poe_view_with_null_fields_emits_no_poe_metrics(aggregator, instance):
    # Virtual switches return every PoE field null. The view still answers 200, so absence -- not
    # an HTTP error -- is how "no PoE hardware" is signalled.
    by_view = dict(CONFIG_ONLY, poE=load_captured('data_interfaces_poe'))

    collect_interfaces(_check(instance), _client(instance, by_view), views=('configuration', 'poE'))

    aggregator.assert_metric('cisco_catalyst_center.interface.poe.power_consumed', count=0)


def test_collect_interfaces_parses_watt_suffixed_poe_strings(aggregator, instance):
    # pdPowerConsumedInWatt is a string with the unit baked in, e.g. "10.5W".
    poe = with_value(load_captured('data_interfaces_poe'), 'response.0.pdPowerConsumedInWatt', '10.5W')
    by_view = dict(CONFIG_ONLY, poE=poe)

    collect_interfaces(_check(instance), _client(instance, by_view), views=('configuration', 'poE'))

    assert metric_values(aggregator, 'cisco_catalyst_center.interface.poe.power_consumed') == [10.5]
