# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors import FirewallState
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, collect_ha

from ..common import FIXTURES
from ..helpers import load_op, load_xml, make_ctx, needs_capture

ENABLED = FIXTURES / 'synthetic' / 'ha_all_enabled.xml'


def test_standalone_firewall_has_no_ha_state_and_no_warning():
    ctx = make_ctx(load_op(HA_CMD), state=FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    ctx.client.op.assert_called_once_with(HA_CMD)
    assert ctx.state.ha_state is None
    ctx.log.warning.assert_not_called()


def test_enabled_firewall_keeps_its_local_state_and_warns_once_about_the_links():
    ctx = make_ctx(load_xml(ENABLED))

    assert collect_ha(ctx) == []
    assert collect_ha(ctx) == []

    assert ctx.state.ha_state == 'active'
    ctx.log.warning.assert_called_once()


def test_enabled_firewall_without_a_local_state_has_none():
    root = load_xml(ENABLED)
    root.find('result/group/local-info').remove(root.find('result/group/local-info/state'))
    ctx = make_ctx(root, state=FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    assert ctx.state.ha_state is None


# Gated on the HA pair lab capture (L1). Expected layout, one `show high-availability all` answer per member:
#   tests/fixtures/ha-pair/active/ha_all.xml
#   tests/fixtures/ha-pair/passive/ha_all.xml
# The link counters are not collected yet: once L1 lands, implement the XPath in `collect_ha` (or, if the counters are
# not in `ha_all`, the per-link `show high-availability interface ha1|ha2` calls) and these tests start running.
HA_PAIR = FIXTURES / 'ha-pair'
HA_LINK_METRICS = {
    'ha.interface.rx.bytes',
    'ha.interface.rx.packets',
    'ha.interface.rx.errors',
    'ha.interface.rx.drops',
    'ha.interface.tx.bytes',
    'ha.interface.tx.packets',
}
needs_ha_pair = needs_capture('ha-pair', 'L1 (HA pair)')


@needs_ha_pair
@pytest.mark.parametrize('member', ['active', 'passive'])
def test_ha_pair_member_sends_six_link_counters_per_link_and_never_the_state(member):
    ctx = make_ctx(load_xml(HA_PAIR / member / 'ha_all.xml'))

    samples = collect_ha(ctx)

    assert ctx.state.ha_state == member
    by_link = {}
    for sample in samples:
        assert sample.name in HA_LINK_METRICS
        assert sample.kind == 'monotonic_count'
        assert sample.value >= 0
        link_tags = [tag for tag in sample.tags if tag.startswith('ha_link:')]
        assert len(link_tags) == 1
        assert not any(tag.startswith('ha_state:') for tag in sample.tags)
        by_link.setdefault(link_tags[0], set()).add(sample.name)
    assert by_link
    assert all(names == HA_LINK_METRICS for names in by_link.values())
