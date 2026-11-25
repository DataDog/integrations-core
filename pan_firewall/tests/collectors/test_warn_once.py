# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from types import SimpleNamespace

import pytest

from datadog_checks.pan_firewall.collectors.counters import collect_global_counters
from datadog_checks.pan_firewall.collectors.dataplane import collect_dataplane
from datadog_checks.pan_firewall.collectors.ha import collect_ha
from datadog_checks.pan_firewall.collectors.interfaces import collect_interfaces
from datadog_checks.pan_firewall.collectors.licenses import collect_licenses
from datadog_checks.pan_firewall.collectors.routing import collect_bgp, collect_ospf
from datadog_checks.pan_firewall.collectors.rules import collect_rule_hits
from datadog_checks.pan_firewall.collectors.system import collect_disk, collect_environment, collect_system_resources
from datadog_checks.pan_firewall.collectors.vpn import collect_vpn
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_IP, SYNTHETIC
from ..helpers import logged, make_ctx

pytestmark = pytest.mark.unit

EMPTY_RESULT = b'<response status="success"><result/></response>'
NO_RESULT = b'<response status="success"/>'
TEXT_RESULT = b'<response status="success"><result>not what was expected</result></response>'
# Answers every call, so the HA1 link call gets a shape without counters.
HA_ENABLED = (
    b'<response status="success"><result><enabled>yes</enabled>'
    b'<group><local-info><ha1-port>management</ha1-port></local-info></group></result></response>'
)
# A power supply in alarm without thresholds: the direction is unknown, so it is warned about, and the other sensors
# are still sent.
HARDWARE = (SYNTHETIC / 'environmentals_hw.xml').read_bytes()

# collector, answer, identity fields, and whether the collector sends nothing for that answer.
CASES = {
    'dataplane': (collect_dataplane, EMPTY_RESULT, {}, True),
    'interfaces': (collect_interfaces, EMPTY_RESULT, {}, True),
    'system_resources': (collect_system_resources, TEXT_RESULT, {}, True),
    'disk': (collect_disk, TEXT_RESULT, {}, True),
    'vpn': (collect_vpn, NO_RESULT, {}, True),
    'licenses': (collect_licenses, EMPTY_RESULT, {}, True),
    'rule_hits': (collect_rule_hits, EMPTY_RESULT, {}, True),
    'global_counters': (collect_global_counters, EMPTY_RESULT, {}, True),
    'ha': (collect_ha, HA_ENABLED, {}, True),
    'bgp': (collect_bgp, EMPTY_RESULT, {'advanced_routing': True}, True),
    'ospf': (collect_ospf, EMPTY_RESULT, {'advanced_routing': True}, True),
    'environment': (collect_environment, HARDWARE, {}, False),
}


@pytest.mark.parametrize('collect, response, identity, sends_nothing', CASES.values(), ids=CASES.keys())
def test_an_unknown_shape_is_warned_about_once_per_firewall_not_once_per_run(
    collect, response, identity, sends_nothing
):
    ctx = make_ctx(
        parse_response(response),
        identity=SimpleNamespace(serial='serial', **identity),
        config=SimpleNamespace(security_rule_filter=None),
    )

    assert (collect(ctx) == []) is sends_nothing
    collect(ctx)

    assert ctx.log.warning.call_count == 1


@pytest.mark.parametrize(
    'once, warned, debugged',
    [
        pytest.param(True, ['a', 'b'], ['a'], id='once-per-key-then-debug'),
        pytest.param(False, ['a', 'a', 'b'], [], id='every-time'),
    ],
)
def test_a_warning_is_logged_once_per_key_then_at_debug_level_unless_once_is_false(once, warned, debugged):
    ctx = make_ctx()

    for sensor in ('a', 'a', 'b'):
        ctx.warning('sensor %s is off', sensor, once=once)

    assert logged(ctx.log.warning) == [f'{FW_A_IP}: sensor {s} is off' for s in warned]
    assert logged(ctx.log.debug) == [f'{FW_A_IP}: sensor {s} is off' for s in debugged]
