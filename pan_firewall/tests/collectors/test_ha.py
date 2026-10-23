# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, collect_ha

from ..common import SYNTHETIC
from ..helpers import load_op, load_xml, make_ctx

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'answer, ha_state',
    [
        pytest.param(load_op(HA_CMD), None, id='standalone'),
        pytest.param(load_xml(SYNTHETIC / 'ha_all_enabled.xml'), 'active', id='enabled'),
    ],
)
def test_each_run_replaces_the_ha_state(answer, ha_state):
    ctx = make_ctx(answer, state=FirewallState(ha_state='passive'))

    collect_ha(ctx)

    assert ctx.state.ha_state == ha_state
