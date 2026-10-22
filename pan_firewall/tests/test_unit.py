# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import re
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pan_firewall import PanFirewallCheck, constants
from datadog_checks.pan_firewall.collectors.ha import HA_CMD
from datadog_checks.pan_firewall.collectors.interfaces import COUNTER_INTERFACE_CMD
from datadog_checks.pan_firewall.collectors.system import ENVIRONMENTALS_CMD
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.xml_utils import num, parse_response, text

from .common import (
    CREDENTIALS,
    FIXTURES,
    FW_A_IP,
    FW_A_PEER,
    FW_A_SERIAL,
    FW_A_TAGS,
    FW_A_TUNNEL,
    INTERFACE_ALL_CMD,
    INTERFACE_CONFIG_CMD,
    SYNTHETIC,
)
from .fake_panos import FIREWALL_SETS, PANORAMA_HOSTS
from .fixture_map import THREAT_LOG_FIRST_SEQNO
from .helpers import THREAT_LOG_ACT, log_page, make_instance

pytestmark = pytest.mark.unit

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

# Who makes requests on each run, by seconds since the first run, for each firewall. The first run makes every
# default-enabled collector's request; a minute later nothing is due, so a collector that polls on every run shows up
# here. The tiers themselves are pinned in `test_scheduler`. `jobs` is the commit check, made on every run that has a
# due collector and on no other.
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
}


def new_static_check():
    instance = {'firewalls': list(FIREWALLS.values()), 'firewall_credentials': CREDENTIALS}
    return PanFirewallCheck('pan_firewall', {}, [instance])


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


def test_each_run_makes_only_the_requests_that_are_due(dd_run_check, fake_panos, schedule_clock):
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


# One row per collector whose samples the check submits as they come: (metric, extra tags). The parser tests pin every
# value; these rows pin that the check submits each collector's metrics with the global tags. A new collector gets its
# row here.
ETHERNET1_1 = (
    'interface:ethernet1/1',
    'interface_type:ethernet',
    'zone:untrust',
    'vsys:vsys1',
    'vr:default',
    f'dd.internal.resource:ndm_interface:{FW_A_SERIAL}',
)
CHECK_LEVEL_SERIES = [
    ('counter.global', ('counter:pkt_recv', 'category:packet', 'aspect:pktproc')),  # global_counters
    ('interface.rx.bytes', ETHERNET1_1),  # interfaces
    ('license.expired', ('feature:pan_db_url_filtering',)),  # licenses
    ('bgp.peer.status', FW_A_PEER),  # bgp
    (
        'ospf.neighbor.status',
        ('neighbor:169.254.10.2', 'router_id:10.255.0.2', 'area:0.0.0.0', 'vr:default'),
    ),  # ospf
    ('security_rule.hits', ('rule:trust-to-vpn', 'vsys:vsys1')),  # rule_hits
    ('mgmt.cpu.user', ()),  # system_resources
    ('dataplane.cpu.utilization', ('dp:dp0', 'core:2')),  # dataplane
    ('disk.used_pct', ('mount:/opt/pancfg', 'filesystem:/dev/nvme0n1p5')),  # disk
    ('ipsec.tunnel.state', FW_A_TUNNEL),  # vpn
    ('power.voltage', ('sensor:Power Supply 3', 'slot:1')),  # environment
    ('report.top.sessions', ('report:top_applications', 'app:ping')),  # reports
]


def test_every_collector_submits_with_the_global_tags(dd_run_check, aggregator, fake_panos):
    # The lab VM has no sensors; the synthetic answer has them.
    fake_panos.answer_op(FW_A_IP, ENVIRONMENTALS_CMD, (200, HARDWARE_ANSWERS[ENVIRONMENTALS_CMD].read_bytes()))
    instance = make_instance(collect_global_counters=True, collect_ospf=True, collect_reports=True)

    dd_run_check(PanFirewallCheck('pan_firewall', {}, [instance]))

    for name, tags in CHECK_LEVEL_SERIES:
        aggregator.assert_metric(f'pan_firewall.{name}', tags=sorted([*FW_A_TAGS, *tags]))
    # One `counter interface all` serves the interfaces and the tunnels.
    commands = collections.Counter(c.cmd for c in fake_panos.calls)
    assert commands[COUNTER_INTERFACE_CMD] == 1


# The synthetic answers for what the lab VMs lack: sensors, interface speeds and an HA pair.
HARDWARE_ANSWERS = {
    ENVIRONMENTALS_CMD: SYNTHETIC / 'environmentals_hw.xml',
    INTERFACE_ALL_CMD: SYNTHETIC / 'interface_all_speeds.xml',
    HA_CMD: SYNTHETIC / 'ha_all_enabled.xml',
}


def test_every_metadata_metric_is_emitted(dd_run_check, aggregator, fake_panos, schedule_clock):
    for name, ip in FIREWALLS.items():
        fake_panos.answer_log(ip, 'backward', None, 0, log_page([THREAT_LOG_FIRST_SEQNO[name] - 1]))
        for cmd, path in HARDWARE_ANSWERS.items():
            fake_panos.answer_op(ip, cmd, (200, path.read_bytes()))
    # A Panorama instance, as only it sends `panorama.can_connect`; it discovers and polls both fake firewalls.
    instance = {
        'panorama_host': next(iter(PANORAMA_HOSTS)),
        'panorama_api_key': 'dummy-api-key',
        'firewall_credentials': CREDENTIALS,
        'collect_global_counters': True,
        'collect_ospf': True,
        'collect_reports': True,
    }
    check = PanFirewallCheck('pan_firewall', {}, [instance])
    start = schedule_clock.now

    for seconds in (0, 180, 300):
        schedule_clock.now = start + seconds
        dd_run_check(check)

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_symmetric_inclusion=True, check_submission_type=True
    )
    # fw-b has its own threat watermark, so the aggregate above is satisfied by fw-a alone; each firewall must report.
    for ip in FIREWALLS.values():
        for name in ('can_connect', 'threat.count'):
            assert any(f'device_ip:{ip}' in m.tags for m in aggregator.metrics(f'pan_firewall.{name}')), (name, ip)
