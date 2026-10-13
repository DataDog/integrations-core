# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall import poller as poller_module
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.interfaces import (
    COUNTER_INTERFACE_CMD,
    collect_interfaces,
    parse_interface_counters,
    parse_interface_speeds,
)
from datadog_checks.pan_firewall.scheduler import FirewallSchedule
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..fixture_map import op_fixture
from ..test_check import FW_A_IP, FW_A_TAGS, INTERFACE_ALL_CMD, new_check

SYNTHETIC = FIXTURES / 'synthetic'
SERIAL = '007955000930601'
COUNTER_FIELDS = {
    'ibytes': 'interface.rx.bytes',
    'obytes': 'interface.tx.bytes',
    'ipackets': 'interface.rx.packets',
    'opackets': 'interface.tx.packets',
    'ierrors': 'interface.rx.errors',
    'idrops': 'interface.rx.drops',
    'ifwderrors': 'interface.forward_errors',
    'flowstate': 'interface.flow_state',
    'land': 'interface.attack.land',
    'pod': 'interface.attack.ping_of_death',
    'teardrop': 'interface.attack.teardrop',
    'ipspoof': 'interface.attack.ip_spoof',
    'macspoof': 'interface.attack.mac_spoof',
}
ZERO = dict.fromkeys(COUNTER_FIELDS, 0)
# Values of the `ifnet/ifnet/entry` rows of the captures, in COUNTER_FIELDS order.
FW_A_ROWS = {
    'ethernet1/1': (153738451, 3120586, 119008, 30547, 0, 0, 0, 3, 0, 0, 0, 0, 0),
    'ethernet1/2': (2213914, 152466233, 25062, 110271, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'loopback': (0,) * 13,
    'loopback.1': (0,) * 13,
    'tunnel': (0,) * 13,
    'tunnel.1': (1563183, 919234, 11275, 5157, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'tunnel.2': (0,) * 13,
}
FW_B_ROWS = {
    'ethernet1/1': (158850809, 3216766, 122598, 31770, 0, 0, 0, 4, 0, 0, 0, 0, 0),
    'ethernet1/2': (2307104, 157577780, 26285, 113879, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'loopback': (0,) * 13,
    'loopback.1': (0,) * 13,
    'tunnel': (0,) * 13,
    'tunnel.1': (1573118, 923056, 11284, 5192, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'tunnel.2': (0,) * 13,
}
FW_A_TUNNELS = {'tunnel.1': (1563183, 919234, 11275, 5157), 'tunnel.2': (0, 0, 0, 0)}
FW_B_TUNNELS = {'tunnel.1': (1573118, 923056, 11284, 5192), 'tunnel.2': (0, 0, 0, 0)}
# interface, interface_type, zone, vsys, vr
MAP_TAGS = {
    'ethernet1/1': ('interface:ethernet1/1', 'interface_type:ethernet', 'zone:untrust', 'vsys:vsys1', 'vr:default'),
    'ethernet1/2': ('interface:ethernet1/2', 'interface_type:ethernet', 'zone:trust', 'vsys:vsys1', 'vr:default'),
    'loopback': ('interface:loopback', 'interface_type:loopback', 'vsys:vsys1'),
    'loopback.1': ('interface:loopback.1', 'interface_type:loopback', 'zone:trust', 'vsys:vsys1', 'vr:default'),
    'tunnel': ('interface:tunnel', 'interface_type:tunnel', 'vsys:vsys1'),
    'tunnel.1': ('interface:tunnel.1', 'interface_type:tunnel', 'zone:vpn', 'vsys:vsys1', 'vr:default'),
    'tunnel.2': ('interface:tunnel.2', 'interface_type:tunnel', 'zone:vpn', 'vsys:vsys1', 'vr:default'),
}


def resource_tag(name):
    # Same shape as hpe_aruba_edgeconnect: the device id only, the `interface` tag identifies the port.
    return f'dd.internal.resource:ndm_interface:{SERIAL}'


def load(path):
    return parse_response(path.read_bytes())


def state_from(path):
    """The state the identity step builds from a `show interface all` answer."""
    root = load(path)
    state = FirewallState()
    state.interface_rows = root.findall('./result/ifnet/entry')
    state.interface_map = {e.findtext('name'): e for e in root.findall('./result/hw/entry')}
    return state


def series(samples):
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def expected_interfaces(rows, tags_of):
    expected = {}
    for name, values in rows.items():
        for metric, value in zip(COUNTER_FIELDS.values(), values):
            expected[metric, tags_of(name)] = (value, 'monotonic_count')
    return expected


def with_map_tags(name):
    return (*MAP_TAGS[name], resource_tag(name))


@pytest.mark.parametrize(
    'firewall, rows', [pytest.param('fw-a', FW_A_ROWS, id='fw-a'), pytest.param('fw-b', FW_B_ROWS, id='fw-b')]
)
def test_interface_counters_with_the_interface_map(firewall, rows):
    state = state_from(FIXTURES / 'fw-a-probe' / 'interface_all.xml')
    samples = parse_interface_counters(
        load(FIXTURES / firewall / 'counter_interface.xml'), state, SERIAL, None, mock.Mock()
    )

    interface_samples = [s for s in samples if s.name.startswith('interface.')]
    assert series(interface_samples) == expected_interfaces(rows, with_map_tags)
    assert len(interface_samples) == 13 * 7


def test_interface_counters_without_a_map_carry_the_interface_tag_only():
    samples = parse_interface_counters(
        load(op_fixture(COUNTER_INTERFACE_CMD, 'fw-b')), FirewallState(), SERIAL, None, mock.Mock()
    )

    interface_samples = [s for s in samples if s.name.startswith('interface.')]
    assert series(interface_samples) == expected_interfaces(FW_B_ROWS, lambda name: (f'interface:{name}',))


def test_interface_without_an_ifnet_row_gets_the_type_and_the_resource_tag():
    state = state_from(FIXTURES / 'fw-a-probe' / 'interface_all.xml')
    state.interface_rows = [r for r in state.interface_rows if r.findtext('name') != 'ethernet1/2']

    samples = parse_interface_counters(load(op_fixture(COUNTER_INTERFACE_CMD)), state, SERIAL, None, mock.Mock())

    tags = {s.tags for s in samples if s.name == 'interface.rx.bytes' and 'interface:ethernet1/2' in s.tags}
    assert tags == {('interface:ethernet1/2', 'interface_type:ethernet', resource_tag('ethernet1/2'))}


def test_resource_tag_is_omitted_without_a_serial():
    state = state_from(FIXTURES / 'fw-a-probe' / 'interface_all.xml')

    samples = parse_interface_counters(load(op_fixture(COUNTER_INTERFACE_CMD)), state, None, None, mock.Mock())

    assert not any('dd.internal.resource' in t for s in samples for t in s.tags)


def tunnel_tags(name):
    return (f'tunnel:tun-{name}', f'tunnel_interface:{name}', 'peer_ip:10.0.0.1', 'gateway:gw', 'outer_interface:e1')


@pytest.mark.parametrize(
    'firewall, tunnels',
    [pytest.param('fw-a', FW_A_TUNNELS, id='fw-a'), pytest.param('fw-b', FW_B_TUNNELS, id='fw-b')],
)
def test_tunnel_rows_become_ipsec_counters_with_the_tags_vpn_stored(firewall, tunnels):
    known = {name: tunnel_tags(name) for name in tunnels}

    samples = parse_interface_counters(
        load(op_fixture(COUNTER_INTERFACE_CMD, firewall)), FirewallState(), SERIAL, known, mock.Mock()
    )

    ipsec = [s for s in samples if s.name.startswith('ipsec.')]
    expected = {}
    for name, values in tunnels.items():
        for metric, value in zip(
            ('ipsec.tunnel.rx.bytes', 'ipsec.tunnel.tx.bytes', 'ipsec.tunnel.rx.packets', 'ipsec.tunnel.tx.packets'),
            values,
        ):
            expected[metric, tunnel_tags(name)] = (value, 'monotonic_count')
    assert series(ipsec) == expected
    # The same rows are also interfaces, tunnels included.
    assert {s.tags[0] for s in samples if s.name == 'interface.rx.bytes'} >= {
        'interface:tunnel.1',
        'interface:tunnel.2',
    }


def test_tunnel_counters_wait_for_the_vpn_tags():
    # A tag-poor series sent before `vpn` answers would be a useless monotonic_count context.
    samples = parse_interface_counters(
        load(op_fixture(COUNTER_INTERFACE_CMD)), FirewallState(), SERIAL, None, mock.Mock()
    )

    assert not [s for s in samples if s.name.startswith('ipsec.')]
    assert [s for s in samples if s.name == 'interface.rx.bytes']


def test_tunnel_row_that_vpn_does_not_list_is_not_an_ipsec_tunnel():
    samples = parse_interface_counters(
        load(op_fixture(COUNTER_INTERFACE_CMD)),
        FirewallState(),
        SERIAL,
        {'tunnel.1': tunnel_tags('tunnel.1')},
        mock.Mock(),
    )

    assert {s.tags for s in samples if s.name == 'ipsec.tunnel.rx.bytes'} == {tunnel_tags('tunnel.1')}


def test_unknown_counter_shape_warns_and_sends_nothing():
    log = mock.Mock()
    root = parse_response(b'<response status="success"><result><ifnet><entry/></ifnet></result></response>')

    assert parse_interface_counters(root, FirewallState(), SERIAL, None, log) == []
    log.warning.assert_called_once()


def test_speeds_of_the_capture_are_not_sent():
    state = state_from(FIXTURES / 'fw-a-probe' / 'interface_all.xml')

    assert parse_interface_speeds(state, SERIAL, mock.Mock()) == []


def test_speed_is_megabits_converted_to_bits_and_unparseable_is_logged():
    state = state_from(SYNTHETIC / 'interface_all_speeds.xml')
    log = mock.Mock()

    samples = parse_interface_speeds(state, SERIAL, log)

    assert series(samples) == {
        ('interface.speed', with_map_tags('ethernet1/1')): (1e9, 'gauge'),
        ('interface.speed', with_map_tags('ethernet1/2')): (1e10, 'gauge'),
    }
    log.debug.assert_called_once()
    assert 'fast' in str(log.debug.call_args)


def test_speed_needs_the_map():
    assert parse_interface_speeds(FirewallState(), SERIAL, mock.Mock()) == []


def make_context(state, response):
    ctx = CollectContext(
        client=mock.Mock(),
        identity=mock.Mock(serial=SERIAL),
        state=state,
        config=mock.Mock(),
        log=mock.Mock(),
    )
    ctx.client.op.return_value = response
    return ctx


def test_collector_makes_one_call_and_leaves_the_speeds_to_the_identity_step():
    state = state_from(SYNTHETIC / 'interface_all_speeds.xml')
    ctx = make_context(state, load(op_fixture(COUNTER_INTERFACE_CMD)))

    samples = collect_interfaces(ctx)

    ctx.client.op.assert_called_once_with(COUNTER_INTERFACE_CMD)
    assert 'interface.rx.bytes' in {s.name for s in samples}
    assert 'interface.speed' not in {s.name for s in samples}


def test_speeds_are_sent_every_30_minutes_with_the_identity_not_every_3(
    dd_run_check, aggregator, fake_panos, monkeypatch
):
    now = [1000.0]
    monkeypatch.setattr(poller_module, 'FirewallSchedule', lambda: FirewallSchedule(lambda: now[0]))
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, (SYNTHETIC / 'interface_all_speeds.xml').read_bytes()))
    check = new_check()

    sent = []
    for seconds in (0, 180, 1799, 1800):
        now[0] = 1000.0 + seconds
        before = len(aggregator.metrics('pan_firewall.interface.speed'))
        dd_run_check(check)
        sent.append(len(aggregator.metrics('pan_firewall.interface.speed')) - before)

    # Two interfaces report a speed: sent on the first run and on the 30-minute run only.
    assert sent == [2, 0, 0, 2]


def test_interfaces_is_registered_and_submits_through_the_check(real_collectors, dd_run_check, aggregator, fake_panos):
    assert 'interfaces' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    assert [c.cmd for c in fake_panos.calls if c.cmd == COUNTER_INTERFACE_CMD] == [COUNTER_INTERFACE_CMD]
    for field, metric in COUNTER_FIELDS.items():
        value = FW_A_ROWS['ethernet1/1'][list(COUNTER_FIELDS).index(field)]
        aggregator.assert_metric(
            f'pan_firewall.{metric}',
            value,
            tags=sorted([*FW_A_TAGS, *with_map_tags('ethernet1/1')]),
            metric_type=aggregator.MONOTONIC_COUNT,
        )
    assert len(aggregator.metrics('pan_firewall.interface.rx.bytes')) == 7
    assert aggregator.metrics('pan_firewall.interface.speed') == []


# Gated on the PA-3420 hardware capture (L8); see test_environment.py for the expected layout. The VM captures carry no
# speed (`ukn`), the hardware one does.
PA_3420 = FIXTURES / 'pa-3420'


@pytest.mark.skipif(
    not PA_3420.is_dir(), reason='Needs lab capture L8 (PA-3420 hardware): tests/fixtures/pa-3420/ missing'
)
def test_pa_3420_speeds_are_sent_in_bits_per_second():
    state = state_from(PA_3420 / 'interface_all.xml')

    samples = parse_interface_speeds(state, SERIAL, mock.Mock())

    assert samples
    assert {s.name for s in samples} == {'interface.speed'}
    # The capture states megabits; bit/s is a multiple of 10**6 and at least 10 Mbit/s.
    assert all(s.kind == 'gauge' and s.value >= 10 * 10**6 and s.value % 10**6 == 0 for s in samples)
