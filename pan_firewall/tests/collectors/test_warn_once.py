# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from types import SimpleNamespace
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.counters import collect_global_counters
from datadog_checks.pan_firewall.collectors.dataplane import collect_dataplane
from datadog_checks.pan_firewall.collectors.ha import collect_ha
from datadog_checks.pan_firewall.collectors.interfaces import collect_interfaces
from datadog_checks.pan_firewall.collectors.licenses import collect_licenses
from datadog_checks.pan_firewall.collectors.routing import collect_bgp, collect_ospf
from datadog_checks.pan_firewall.collectors.rules import collect_rule_hits
from datadog_checks.pan_firewall.collectors.system import collect_disk, collect_system_resources
from datadog_checks.pan_firewall.collectors.vpn import collect_vpn
from datadog_checks.pan_firewall.xml_utils import parse_response

EMPTY_RESULT = b'<response status="success"><result/></response>'
NO_RESULT = b'<response status="success"/>'
TEXT_RESULT = b'<response status="success"><result>not what was expected</result></response>'
HA_ENABLED = b'<response status="success"><result><enabled>yes</enabled></result></response>'

CASES = {
    'dataplane': (collect_dataplane, EMPTY_RESULT, {}),
    'interfaces': (collect_interfaces, EMPTY_RESULT, {}),
    'system_resources': (collect_system_resources, TEXT_RESULT, {}),
    'disk': (collect_disk, TEXT_RESULT, {}),
    'vpn': (collect_vpn, NO_RESULT, {}),
    'licenses': (collect_licenses, EMPTY_RESULT, {}),
    'rule_hits': (collect_rule_hits, EMPTY_RESULT, {}),
    'global_counters': (collect_global_counters, EMPTY_RESULT, {}),
    'ha': (collect_ha, HA_ENABLED, {}),
    'bgp': (collect_bgp, EMPTY_RESULT, {'advanced_routing': True}),
    'ospf': (collect_ospf, EMPTY_RESULT, {'advanced_routing': True}),
}


def context(state, response, identity):
    ctx = CollectContext(
        client=mock.Mock(),
        identity=SimpleNamespace(serial='serial', **identity),
        state=state,
        config=SimpleNamespace(security_rule_filter=None),
        log=mock.Mock(),
    )
    ctx.client.op.return_value = parse_response(response)
    return ctx


@pytest.mark.parametrize('collect, response, identity', CASES.values(), ids=CASES.keys())
def test_an_unknown_shape_is_warned_about_once_per_firewall_not_once_per_run(collect, response, identity):
    state = FirewallState()

    ctx = context(state, response, identity)
    collect(ctx)
    collect(ctx)
    assert ctx.log.warning.call_count == 1

    # Another firewall has its own state, so it warns again.
    other = context(FirewallState(), response, identity)
    collect(other)
    assert other.log.warning.call_count == 1
