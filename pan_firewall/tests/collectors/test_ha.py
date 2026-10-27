# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, HA_INTERFACE_CMD, collect_ha, parse_ha_interface
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..helpers import load_op, load_xml, make_ctx, series

pytestmark = pytest.mark.unit

FW_C = FIXTURES / 'fw-c'
HA1 = ('ha_link:ha1',)
HA2 = ('ha_link:ha2',)


def pair_answers(ha1=None):
    """The answers of the fw-c HA pair; `ha1` replaces the answer to the HA1 link."""
    return {
        HA_CMD: load_xml(FW_C / 'ha_all.xml'),
        HA_INTERFACE_CMD.format(link='ha1'): load_xml(FW_C / 'ha_interface_ha1.xml') if ha1 is None else ha1,
        HA_INTERFACE_CMD.format(link='ha2'): load_xml(FW_C / 'ha_interface_ha2.xml'),
    }


def test_management_port_link_counters():
    samples = parse_ha_interface(load_xml(FW_C / 'ha_interface_ha1.xml'), 'ha1')

    assert series(samples) == {
        ('ha.interface.rx.bytes', HA1): (5142963622, 'monotonic_count'),
        ('ha.interface.rx.packets', HA1): (4191607, 'monotonic_count'),
        ('ha.interface.rx.errors', HA1): (0, 'monotonic_count'),
        ('ha.interface.rx.drops', HA1): (0, 'monotonic_count'),
        ('ha.interface.tx.bytes', HA1): (86920467, 'monotonic_count'),
        ('ha.interface.tx.packets', HA1): (1140836, 'monotonic_count'),
    }


def test_dataplane_port_link_counters_come_from_the_port_block():
    samples = parse_ha_interface(load_xml(FW_C / 'ha_interface_ha2.xml'), 'ha2')

    # tx.bytes 309660 is the port block's; the ifnet blocks say 216762.
    assert series(samples) == {
        ('ha.interface.rx.bytes', HA2): (217224, 'monotonic_count'),
        ('ha.interface.rx.packets', HA2): (5172, 'monotonic_count'),
        ('ha.interface.rx.errors', HA2): (0, 'monotonic_count'),
        ('ha.interface.rx.drops', HA2): (0, 'monotonic_count'),
        ('ha.interface.tx.bytes', HA2): (309660, 'monotonic_count'),
        ('ha.interface.tx.packets', HA2): (5161, 'monotonic_count'),
    }


def test_dataplane_shape_on_ha1_is_tagged_ha1():
    # Hardware firewalls can run HA1 on a dedicated dataplane port: the shape decides, not the link name.
    samples = parse_ha_interface(load_xml(FW_C / 'ha_interface_ha2.xml'), 'ha1')

    assert len(samples) == 6
    assert {s.tags for s in samples} == {HA1}
    assert series(samples)[('ha.interface.tx.bytes', HA1)] == (309660, 'monotonic_count')


def test_dataplane_packets_are_not_sent_when_a_cast_counter_is_missing():
    root = load_xml(FW_C / 'ha_interface_ha2.xml')
    port = root.find('result/entry/ifnet/counters/hw/entry/port')
    port.remove(port.find('rx-multicast'))

    names = {s.name for s in parse_ha_interface(root, 'ha2')}

    assert 'ha.interface.rx.packets' not in names
    assert 'ha.interface.tx.packets' in names


def test_unknown_shape_is_none():
    root = parse_response(b'<response status="success"><result/></response>')

    assert parse_ha_interface(root, 'ha1') is None


@pytest.mark.parametrize(
    'answers, ha_state, calls',
    [
        pytest.param({HA_CMD: load_op(HA_CMD)}, None, 1, id='standalone'),
        pytest.param(pair_answers(), 'active', 3, id='enabled'),
    ],
)
def test_each_run_replaces_the_ha_state(answers, ha_state, calls):
    ctx = make_ctx(answers, state=FirewallState(ha_state='passive'))

    collect_ha(ctx)

    assert ctx.state.ha_state == ha_state
    assert ctx.client.op.call_count == calls


def test_enabled_pair_sets_state_and_collects_both_links():
    ctx = make_ctx(pair_answers())

    samples = collect_ha(ctx)

    assert len(samples) == 12
    assert {s.tags for s in samples} == {HA1, HA2}
    assert ctx.state.ha_state == 'active'
    ctx.log.warning.assert_not_called()


def test_unknown_link_shape_warns_once_and_keeps_the_other_link():
    unknown = parse_response(b'<response status="success"><result/></response>')
    ctx = make_ctx(pair_answers(ha1=unknown))

    first, second = collect_ha(ctx), collect_ha(ctx)

    for samples in (first, second):
        assert len(samples) == 6
        assert {s.tags for s in samples} == {HA2}
    ctx.log.warning.assert_called_once()
