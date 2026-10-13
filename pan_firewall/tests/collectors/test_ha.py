# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, collect_ha
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..fixture_map import op_fixture
from ..test_check import new_check

ENABLED = FIXTURES / 'synthetic' / 'ha_all_enabled.xml'


def context(root, state=None):
    ctx = CollectContext(
        client=mock.Mock(), identity=mock.Mock(), state=state or FirewallState(), config=mock.Mock(), log=mock.Mock()
    )
    ctx.client.op.return_value = root
    return ctx


@pytest.mark.parametrize('firewall', ['fw-a', 'fw-b'])
def test_standalone_firewall_has_no_ha_state_and_no_warning(firewall):
    ctx = context(parse_response(op_fixture(HA_CMD, firewall).read_bytes()), FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    ctx.client.op.assert_called_once_with(HA_CMD)
    assert ctx.state.ha_state is None
    ctx.log.warning.assert_not_called()


def test_enabled_firewall_keeps_its_local_state_and_warns_once_about_the_links():
    ctx = context(parse_response(ENABLED.read_bytes()))

    assert collect_ha(ctx) == []
    assert collect_ha(ctx) == []

    assert ctx.state.ha_state == 'active'
    ctx.log.warning.assert_called_once()


def test_enabled_firewall_without_a_local_state_has_none():
    root = parse_response(ENABLED.read_bytes())
    root.find('result/group/local-info').remove(root.find('result/group/local-info/state'))
    ctx = context(root, FirewallState(ha_state='active'))

    assert collect_ha(ctx) == []

    assert ctx.state.ha_state is None


def test_ha_is_registered_and_sends_nothing_through_the_check(real_collectors, dd_run_check, aggregator):
    assert 'ha' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    assert not [name for name in aggregator.metric_names if name.startswith('pan_firewall.ha.')]
