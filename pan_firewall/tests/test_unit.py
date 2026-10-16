# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import re
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pan_firewall import PanFirewallCheck, constants
from datadog_checks.pan_firewall.collectors.interfaces import COUNTER_INTERFACE_CMD
from datadog_checks.pan_firewall.constants import REPORTS
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.xml_utils import num, parse_response, text

from .common import (
    CREDENTIALS,
    FIXTURES,
    FW_A_PEER,
    FW_A_SERIAL,
    FW_A_TAGS,
    FW_A_TUNNEL,
    INTERFACE_CONFIG_CMD,
    SYSTEM_INFO_CMD,
)
from .fake_panos import FIREWALL_SETS
from .fixture_map import (
    LOG_FIXTURES,
    OP_FIXTURES,
    PANORAMA_OP_FIXTURES,
    PARTIAL_OP_FIXTURES,
    SUBMIT_TEMPLATE_IDS,
    SUBMIT_TEMPLATES,
    THREAT_LOG_FIRST_SEQNO,
    find_report_fixture,
    op_fixture,
    submit_answer,
)
from .helpers import THREAT_LOG_ACT, log_page, make_instance

# Patterns that mean a credential value was captured. The bare word "password" is not one of them: real fixtures
# legitimately contain `<password-set>no</password-set>` and threat names such as "/etc/passwd Access Attempt".
SECRET_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (r'<key>', r'LUFRPT', r'<password>', r'password=', r'key=', r'X-PAN-KEY', r'Cookie:', r'<authcode>[^<]')
]


@pytest.mark.parametrize(
    'body, code, msg',
    [
        pytest.param(
            (FIXTURES / 'fw-a-probe' / 'report_top-rules.xml').read_bytes(),
            '400',
            'Illegal value for parameter "reportname"',
            id='with-code',
        ),
        pytest.param(
            b'<response status="error"><msg><line>Invalid credentials.</line></msg></response>',
            '',
            'Invalid credentials.',
            id='without-code',
        ),
    ],
)
def test_parse_response_error(body, code, msg):
    with pytest.raises(PanosApiError) as exc_info:
        parse_response(body)

    assert exc_info.value.code == code
    assert msg in exc_info.value.msg


@pytest.mark.parametrize(
    'body',
    [
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
        ('<r><v>unknown</v></r>', 'v', None),
        ('<r></r>', 'v', None),
        ('<r><v>nan</v></r>', 'v', None),
    ],
)
def test_num_never_raises(xml, path, expected):
    assert num(ET.fromstring(xml), path) == expected


def test_num_and_text_on_missing_element():
    assert num(None, 'v') is None
    assert text(None, 'v', 'fallback') == 'fallback'


def test_fixture_map_points_at_existing_files():
    # fw-b answers with fw-a's file where it has none of its own (`set_fixture`), except for its identity.
    assert (FIXTURES / 'fw-b' / OP_FIXTURES[SYSTEM_INFO_CMD]).is_file()
    for firewall in ('fw-a', 'fw-b'):
        for cmd in OP_FIXTURES:
            assert op_fixture(cmd, firewall).is_file()
        for field, _tag in REPORTS.values():
            assert find_report_fixture(field, firewall), (field, firewall)
    for paths in PARTIAL_OP_FIXTURES.values():
        for relative in paths.values():
            assert (FIXTURES / relative).is_file()
    for jobs in LOG_FIXTURES.values():
        for response in jobs.values():
            assert (FIXTURES / response).is_file()
    for relative in SUBMIT_TEMPLATES.values():
        assert (FIXTURES / relative).is_file()
    for relative in PANORAMA_OP_FIXTURES.values():
        assert (FIXTURES / relative).is_file()


@pytest.mark.parametrize('kind', ['log', 'report'])
def test_submit_answer_with_the_captures_own_id_is_the_capture(kind):
    # A substitution that touched anything but the two id occurrences would make the fakes answer with a different
    # shape than the one PAN-OS sent.
    capture = (FIXTURES / SUBMIT_TEMPLATES[kind]).read_bytes()
    assert submit_answer(kind, SUBMIT_TEMPLATE_IDS[kind]) == capture


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


FIREWALLS = {name: ip for ip, name in FIREWALL_SETS.items()}

GAUGE = 'gauge'
MONOTONIC = 'monotonic_count'

# The P0 metrics the captured lab firewalls produce on their first default run, with their types. Absent on purpose:
# `ha.interface.*` (standalone firewalls), `power.*` and `temperature.*` (VM-Series has no sensors),
# `interface.speed` (VM-Series reports no speed). `threat.count` and the tunnel counters are not on the first run:
# the first threat run only records the newest log as a watermark, and `interfaces` sends the tunnel counters once
# `vpn` has stored the tunnel tags, so from the second 3-minute tier.
TUNNEL_COUNTERS = {
    'ipsec.tunnel.rx.bytes': MONOTONIC,
    'ipsec.tunnel.rx.packets': MONOTONIC,
    'ipsec.tunnel.tx.bytes': MONOTONIC,
    'ipsec.tunnel.tx.packets': MONOTONIC,
}

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
    'ipsec.tunnel.state': GAUGE,
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
    INTERFACE_CONFIG_CMD: 'identity_metadata',
    '<request><license><info/></license></request>': 'licenses',
}

# Who makes requests on each run, by seconds since the first run, for each firewall: only the collectors that are due
# (the tiers themselves are pinned in `test_scheduler`). `jobs` is the commit check, made on every run that has a due
# collector and on no other.
EXPECTED_CALLERS = {
    0: {
        'keygen',
        'jobs',
        'bgp',
        'dataplane',
        'interfaces',
        'system_resources',
        'vpn',
        'ha',
        'rule_hits',
        'environment',
        'threats',
        'disk',
        'identity_metadata',
        'licenses',
    },
    60: set(),
    120: {'jobs', 'bgp', 'dataplane'},
    180: {'jobs', 'interfaces', 'system_resources', 'vpn', 'ha', 'rule_hits'},
    300: {'jobs', 'bgp', 'dataplane', 'environment', 'threats'},
}


def new_static_check():
    instance = {'firewalls': list(FIREWALLS.values()), 'firewall_credentials': CREDENTIALS}
    return PanFirewallCheck('pan_firewall', {}, [instance])


def metrics_of(aggregator, ip):
    """The (name without prefix, type) of every metric submitted for the firewall."""
    types = {aggregator.GAUGE: GAUGE, aggregator.MONOTONIC_COUNT: MONOTONIC, aggregator.COUNT: 'count'}
    return {
        (name.removeprefix('pan_firewall.'), types[metric.type])
        for name in aggregator.metric_names
        for metric in aggregator.metrics(name)
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


def test_runs_at_0_180_and_300_seconds_submit_every_lab_available_p0_metric(
    dd_run_check, aggregator, fake_panos, real_collectors, schedule_clock
):
    # The first threat run reads the newest log as a watermark; start it just below each capture so the 5-minute
    # run counts it.
    for name, ip in FIREWALLS.items():
        fake_panos.answer_log(ip, 'backward', None, 0, log_page([THREAT_LOG_FIRST_SEQNO[name] - 1]))
    check = new_static_check()
    start = schedule_clock.now
    expected = {**FIRST_RUN_METRICS, **TUNNEL_COUNTERS, 'threat.count': 'count'}

    for seconds in (0, 180, 300):
        schedule_clock.now = start + seconds
        dd_run_check(check)

    for ip in FIREWALLS.values():
        assert metrics_of(aggregator, ip) == set(expected.items())
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_each_run_makes_only_the_requests_that_are_due(dd_run_check, fake_panos, real_collectors, schedule_clock):
    check = new_static_check()
    start = schedule_clock.now

    for seconds, expected in EXPECTED_CALLERS.items():
        schedule_clock.now = start + seconds
        calls_before = len(fake_panos.calls)
        dd_run_check(check)

        for ip in FIREWALLS.values():
            assert set(call_labels(fake_panos, ip, calls_before)) == expected, f'run at +{seconds}s on {ip}'


def test_a_threat_job_still_running_is_polled_again_on_the_next_run_not_in_5_minutes(
    dd_run_check,
    fake_panos,
    real_collectors,
    monkeypatch,
    schedule_clock,
):
    monkeypatch.setattr(constants, 'THREAT_JOB_POLLS', 1)
    monkeypatch.setattr(constants, 'THREAT_JOB_POLL_DELAY', 0)
    ip = FIREWALLS['fw-a']
    fake_panos.answer_log(ip, 'backward', None, 0, THREAT_LOG_ACT, log_page([1]))
    check = new_static_check()
    dd_run_check(check)

    schedule_clock.now += 60
    before = len(fake_panos.calls)
    dd_run_check(check)
    assert call_labels(fake_panos, ip, before) == {'jobs': 1, 'threats': 1}

    # The job finished: the collector is on its 5-minute interval again.
    schedule_clock.now += 60
    before = len(fake_panos.calls)
    dd_run_check(check)
    assert 'threats' not in call_labels(fake_panos, ip, before)


# One row per collector whose samples the check submits as they come: (metric, extra tags, type). The parser tests pin
# every value; these rows pin that the check submits each collector's metrics with the right type and the global tags.
ETHERNET1_1 = (
    'interface:ethernet1/1',
    'interface_type:ethernet',
    'zone:untrust',
    'vsys:vsys1',
    'vr:default',
    f'dd.internal.resource:ndm_interface:{FW_A_SERIAL}',
)
CHECK_LEVEL_SERIES = [
    ('counter.global', ('counter:pkt_recv', 'category:packet', 'aspect:pktproc'), MONOTONIC),  # global_counters
    ('interface.rx.bytes', ETHERNET1_1, MONOTONIC),  # interfaces
    ('license.expired', ('feature:pan_db_url_filtering',), GAUGE),  # licenses
    ('bgp.peer.status', FW_A_PEER, GAUGE),  # bgp
    (
        'ospf.neighbor.status',
        ('neighbor:169.254.10.2', 'router_id:10.255.0.2', 'area:0.0.0.0', 'vr:default'),
        GAUGE,
    ),  # ospf
    ('security_rule.hits', ('rule:trust-to-vpn', 'vsys:vsys1'), MONOTONIC),  # rule_hits
    ('mgmt.cpu.user', (), GAUGE),  # system_resources
    ('dataplane.cpu.utilization', ('dp:dp0', 'core:2'), GAUGE),  # dataplane
    ('disk.used_pct', ('mount:/opt/pancfg', 'filesystem:/dev/nvme0n1p5'), GAUGE),  # disk
    ('ipsec.tunnel.state', FW_A_TUNNEL, GAUGE),  # vpn
]


def test_every_collector_submits_with_type_and_tags(dd_run_check, aggregator, fake_panos, real_collectors):
    dd_run_check(PanFirewallCheck('pan_firewall', {}, [make_instance(collect_global_counters=True, collect_ospf=True)]))

    metric_types = {GAUGE: aggregator.GAUGE, MONOTONIC: aggregator.MONOTONIC_COUNT}
    for name, tags, metric_type in CHECK_LEVEL_SERIES:
        aggregator.assert_metric(
            f'pan_firewall.{name}', tags=sorted([*FW_A_TAGS, *tags]), metric_type=metric_types[metric_type]
        )
    # One `counter interface all` serves the interfaces and the tunnels.
    commands = collections.Counter(c.cmd for c in fake_panos.calls)
    assert commands[COUNTER_INTERFACE_CMD] == 1
