# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import re
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall import poller as poller_module
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.scheduler import FirewallSchedule
from datadog_checks.pan_firewall.xml_utils import num, parse_response, text

from .collectors.test_threats import log_page
from .common import CREDENTIALS, FIXTURES
from .fixture_map import OP_FIXTURES, PARTIAL_OP_FIXTURES, THREAT_LOG_FIRST_SEQNO, op_fixture

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'

# Patterns that mean a credential value was captured. The bare word "password" is not one of them: real fixtures
# legitimately contain `<password-set>no</password-set>` and threat names such as "/etc/passwd Access Attempt".
SECRET_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (r'<key>', r'LUFRPT', r'<password>', r'password=', r'key=', r'X-PAN-KEY', r'Cookie:')
]


def test_check_runs(dd_run_check, instance):
    dd_run_check(PanFirewallCheck('pan_firewall', {}, [instance]))


def test_parse_response_system_info():
    root = parse_response(op_fixture(SYSTEM_INFO_CMD).read_bytes())

    assert root.get('status') == 'success'
    assert text(root, './result/system/hostname') == 'fw-a'
    assert text(root, './result/system/sw-version') == '11.1.13-h12'
    assert num(root, './result/system/vm-cores') == 4


def test_parse_response_error_code():
    body = (FIXTURES / 'fw-a-probe' / 'report_top-rules.xml').read_bytes()

    with pytest.raises(PanosApiError) as exc_info:
        parse_response(body)

    assert exc_info.value.code == '400'
    assert 'Illegal value for parameter "reportname"' in exc_info.value.msg


def test_parse_response_error_without_code():
    with pytest.raises(PanosApiError) as exc_info:
        parse_response(b'<response status="error"><msg><line>Invalid credentials.</line></msg></response>')

    assert exc_info.value.code == ''
    assert exc_info.value.msg == 'Invalid credentials.'


@pytest.mark.parametrize(
    'body',
    [
        b'<html><body>Bad Gateway',
        b'',
        b'not xml at all',
        # A proxy error page that happens to be well-formed XML must not pass as a PAN-OS success.
        b'<html><body>502 Bad Gateway</body></html>',
    ],
)
def test_parse_response_non_xml(body):
    with pytest.raises(PanosApiError) as exc_info:
        parse_response(body)

    assert exc_info.value.code == 'parse'


@pytest.mark.parametrize(
    'xml, path, expected',
    [
        ('<r><v>3.5</v></r>', 'v', 3.5),
        ('<r><v> 7 </v></r>', 'v', 7.0),
        ('<r><v>unknown</v></r>', 'v', None),
        ('<r><v></v></r>', 'v', None),
        ('<r></r>', 'v', None),
        ('<r><v>nan</v></r>', 'v', None),
        ('<r><v>-inf</v></r>', 'v', None),
    ],
)
def test_num_never_raises(xml, path, expected):
    assert num(ET.fromstring(xml), path) == expected


def test_num_and_text_on_missing_element():
    assert num(None, 'v') is None
    assert text(None, 'v', 'fallback') == 'fallback'


def test_fixture_map_points_at_existing_files():
    for firewall in ('fw-a', 'fw-b'):
        for cmd in OP_FIXTURES:
            assert op_fixture(cmd, firewall).is_file()
    for paths in PARTIAL_OP_FIXTURES.values():
        for relative in paths.values():
            assert (FIXTURES / relative).is_file()


def test_fixtures_hold_no_secrets():
    files = [p for p in FIXTURES.rglob('*') if p.is_file()]
    assert files
    leaks = [
        (p.relative_to(FIXTURES).as_posix(), pattern.pattern)
        for p in files
        for pattern in SECRET_PATTERNS
        if pattern.search(p.read_text(encoding='utf-8', errors='replace'))
    ]
    assert leaks == []


FIREWALLS = {'fw-a': '192.0.2.10', 'fw-b': '192.0.2.11'}

GAUGE = 'gauge'
MONOTONIC = 'monotonic_count'

# The P0 metrics the captured lab firewalls produce on their first default run, with their types. Absent on purpose:
# `ha.interface.*` (standalone firewalls), `power.*` and `temperature.*` (VM-Series has no sensors),
# `interface.speed` (VM-Series reports no speed), and `threat.count` (the first threat run only records the newest
# log as a watermark, so it counts nothing).
FIRST_RUN_METRICS = {
    'api.authentication.status': GAUGE,
    'bgp.peer.prefix_limit': GAUGE,
    'bgp.peer.prefix_limit.utilization': GAUGE,
    'bgp.peer.prefixes.incoming.rejected': GAUGE,
    'bgp.peer.prefixes.incoming.total': GAUGE,
    'bgp.peer.prefixes.outgoing.advertised': GAUGE,
    'bgp.peer.prefixes.outgoing.total': GAUGE,
    'bgp.peer.restart': GAUGE,
    'bgp.peer.status': GAUGE,
    'bgp.peer.status_duration': GAUGE,
    'bgp.peer.updates.in': MONOTONIC,
    'bgp.peer.updates.out': MONOTONIC,
    'can_connect': GAUGE,
    'dataplane.cpu.utilization': GAUGE,
    'disk.used_pct': GAUGE,
    'interface.attack.ip_spoof': MONOTONIC,
    'interface.attack.land': MONOTONIC,
    'interface.attack.mac_spoof': MONOTONIC,
    'interface.attack.ping_of_death': MONOTONIC,
    'interface.attack.teardrop': MONOTONIC,
    'interface.flow_state': MONOTONIC,
    'interface.forward_errors': MONOTONIC,
    'interface.rx.bytes': MONOTONIC,
    'interface.rx.drops': MONOTONIC,
    'interface.rx.errors': MONOTONIC,
    'interface.rx.packets': MONOTONIC,
    'interface.tx.bytes': MONOTONIC,
    'interface.tx.packets': MONOTONIC,
    'ipsec.gateways.total': GAUGE,
    'ipsec.tunnel.rx.bytes': MONOTONIC,
    'ipsec.tunnel.rx.packets': MONOTONIC,
    'ipsec.tunnel.state': GAUGE,
    'ipsec.tunnel.tx.bytes': MONOTONIC,
    'ipsec.tunnel.tx.packets': MONOTONIC,
    'ipsec.tunnels.active': GAUGE,
    'ipsec.tunnels.inactive': GAUGE,
    'ipsec.tunnels.init': GAUGE,
    'ipsec.tunnels.total': GAUGE,
    'license.days_left': GAUGE,
    'license.expired': GAUGE,
    'mgmt.cpu.hardirq': GAUGE,
    'mgmt.cpu.idle': GAUGE,
    'mgmt.cpu.iowait': GAUGE,
    'mgmt.cpu.nice': GAUGE,
    'mgmt.cpu.softirq': GAUGE,
    'mgmt.cpu.steal': GAUGE,
    'mgmt.cpu.system': GAUGE,
    'mgmt.cpu.used': GAUGE,
    'mgmt.cpu.user': GAUGE,
    'mgmt.memory.available': GAUGE,
    'mgmt.memory.buff_cache': GAUGE,
    'mgmt.memory.free': GAUGE,
    'mgmt.memory.total': GAUGE,
    'mgmt.memory.used': GAUGE,
    'mgmt.memory.used_pct': GAUGE,
    'mgmt.swap.free': GAUGE,
    'mgmt.swap.total': GAUGE,
    'mgmt.swap.used': GAUGE,
    'mgmt.swap.used_pct': GAUGE,
    'security_rule.hits': MONOTONIC,
}

# Which collector (or step) a request belongs to, by the `cmd` it sends. `type=log` requests are the threat jobs.
CMD_LABELS = {
    '<show><jobs><pending/></jobs></show>': 'jobs',
    '<show><routing><protocol><bgp><peer/></bgp></protocol></routing></show>': 'bgp',
    '<show><running><resource-monitor><minute><last>1</last></minute></resource-monitor></running></show>': 'dataplane',
    '<show><counter><interface>all</interface></counter></show>': 'interfaces',
    '<show><system><resources/></system></show>': 'system_resources',
    '<show><vpn><flow/></vpn></show>': 'vpn',
    '<show><vpn><gateway/></vpn></show>': 'vpn',
    '<show><high-availability><all/></high-availability></show>': 'ha',
    '<show><system><environmentals/></system></show>': 'environment',
    '<show><system><disk-space/></system></show>': 'disk',
    '<show><system><info/></system></show>': 'identity_metadata',
    '<show><interface>all</interface></show>': 'identity_metadata',
    '<request><license><info/></license></request>': 'licenses',
}

# Requests per run, by seconds since the first run, for each firewall (plan section 2.4, "Schedule"). `jobs` is the
# commit check: one request on every run that has a due collector, none on a run with nothing due. The 3-minute tier
# is 5 + V requests (`interfaces` 1, `system_resources` 1, `vpn` 2, `ha` 1, and `rule_hits` V = 1 per vsys). A
# first threat run asks one `backward` job and reads it (2); a later one submits a `forward` job and reads it (2).
EXPECTED_CALLS = {
    0: {
        'keygen': 1,
        'jobs': 1,
        'bgp': 1,
        'dataplane': 1,
        'interfaces': 1,
        'system_resources': 1,
        'vpn': 2,
        'ha': 1,
        'rule_hits': 1,
        'environment': 1,
        'threats': 2,
        'disk': 1,
        'identity_metadata': 2,
        'licenses': 1,
    },
    60: {},
    120: {'jobs': 1, 'bgp': 1, 'dataplane': 1},
    180: {'jobs': 1, 'interfaces': 1, 'system_resources': 1, 'vpn': 2, 'ha': 1, 'rule_hits': 1},
    300: {'jobs': 1, 'bgp': 1, 'dataplane': 1, 'environment': 1, 'threats': 2},
}


def new_static_check():
    instance = {'firewalls': list(FIREWALLS.values()), 'firewall_credentials': CREDENTIALS}
    return PanFirewallCheck('pan_firewall', {}, [instance])


def metrics_of(aggregator, ip):
    """The (name without prefix, type) of every metric submitted for the firewall."""
    types = {aggregator.GAUGE: GAUGE, aggregator.MONOTONIC_COUNT: MONOTONIC, aggregator.COUNT: 'count'}
    return {
        (name.removeprefix('pan_firewall.'), types[metric.type])
        for name, stubs in aggregator._metrics.items()
        for metric in stubs
        if f'device_ip:{ip}' in metric.tags
    }


def call_labels(fake_panos, ip, since):
    labels = collections.Counter()
    for call in fake_panos.calls[since:]:
        if call.host != ip:
            continue
        if call.type == 'keygen':
            labels['keygen'] += 1
        elif call.type == 'log':
            labels['threats'] += 1
        else:
            labels[CMD_LABELS.get(call.cmd, call.cmd)] += 1
            if call.cmd.startswith('<show><rule-hit-count>'):
                labels['rule_hits'] += 1
                labels.pop(call.cmd)
    return dict(labels)


def test_first_run_submits_every_lab_available_p0_metric(dd_run_check, aggregator, real_collectors):
    dd_run_check(new_static_check())

    for ip in FIREWALLS.values():
        assert metrics_of(aggregator, ip) == set(FIRST_RUN_METRICS.items())
    for name, metric_type in FIRST_RUN_METRICS.items():
        aggregator.assert_metric(
            f'pan_firewall.{name}',
            metric_type={GAUGE: aggregator.GAUGE, MONOTONIC: aggregator.MONOTONIC_COUNT}[metric_type],
            at_least=1,
        )
    aggregator.assert_all_metrics_covered()


def test_each_run_makes_only_the_requests_that_are_due(
    dd_run_check, aggregator, fake_panos, real_collectors, monkeypatch
):
    now = [1000.0]
    monkeypatch.setattr(poller_module, 'FirewallSchedule', lambda: FirewallSchedule(lambda: now[0]))
    # The first threat run reads the newest log as a watermark; start it just below each capture so the 5-minute
    # run counts it.
    for name, ip in FIREWALLS.items():
        fake_panos.answer_log(ip, 'backward', None, 0, log_page([THREAT_LOG_FIRST_SEQNO[name] - 1]))
    check = new_static_check()
    start = now[0]

    for seconds, expected in EXPECTED_CALLS.items():
        now[0] = start + seconds
        calls_before = len(fake_panos.calls)
        dd_run_check(check)

        for ip in FIREWALLS.values():
            assert call_labels(fake_panos, ip, calls_before) == expected, f'run at +{seconds}s on {ip}'

    for ip in FIREWALLS.values():
        assert ('threat.count', 'count') in metrics_of(aggregator, ip)
