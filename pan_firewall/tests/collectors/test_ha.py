# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, collect_ha

from ..common import FIXTURES
from ..helpers import load_op, load_xml, make_ctx

ENABLED = FIXTURES / 'synthetic' / 'ha_all_enabled.xml'


def test_standalone_firewall_has_no_ha_state():
    ctx = make_ctx(load_op(HA_CMD), state=FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    ctx.client.op.assert_called_once_with(HA_CMD)
    assert ctx.state.ha_state is None


def test_enabled_firewall_keeps_its_local_state():
    ctx = make_ctx(load_xml(ENABLED))

    assert collect_ha(ctx) == []

    assert ctx.state.ha_state == 'active'


def test_enabled_firewall_without_a_local_state_has_none():
    root = load_xml(ENABLED)
    root.find('result/group/local-info').remove(root.find('result/group/local-info/state'))
    ctx = make_ctx(root, state=FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    assert ctx.state.ha_state is None
