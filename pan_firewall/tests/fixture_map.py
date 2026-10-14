# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Maps a PAN-OS API request to a captured fixture file, and holds the fake API's fixed answers.

Shared by the unit fake transport and the docker fakes, so both answer from the same data. The docker fakes import
it without the test dependencies, so it imports nothing from the other test modules.
"""

import re
from collections.abc import Mapping
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

# The keygen success shape (`result/key`) from the PAN-OS XML API docs ("Get Your API Key"), with a dummy key. Kept
# inline rather than in `fixtures/synthetic/`: fixture files must hold no `<key>` (see `test_fixtures_hold_no_secrets`).
FAKE_KEY = 'FAKE-KEY-0000'
KEYGEN_OK = f'<response status="success"><result><key>{FAKE_KEY}</key></result></response>'.encode()
INVALID_CREDENTIAL = (FIXTURES / 'synthetic' / 'auth_invalid_credential.xml').read_bytes()
# Stand-in for a command the fixture set has no capture for (for example `show interface all` on fw-b): PAN-OS
# answers commands it cannot run with `status="error"`.
NO_CAPTURE = b'<response status="error" code="400"><msg><line>no capture for this command</line></msg></response>'

# `type=op` commands, as sent by the live captures, to the fixture file name.
OP_FIXTURES = {
    '<show><system><info/></system></show>': 'system_info.xml',
    '<show><routing><protocol><bgp><peer/></bgp></protocol></routing></show>': 'bgp_peer_legacy.xml',
    '<show><routing><protocol><ospf><neighbor/></ospf></protocol></routing></show>': 'ospf_neighbor_legacy.xml',
    '<show><running><resource-monitor><minute><last>1</last></minute></resource-monitor></running></show>': (
        'resource_monitor.xml'
    ),
    '<show><system><disk-space/></system></show>': 'disk_space.xml',
    '<show><rule-hit-count><vsys><vsys-name><entry name=\'vsys1\'><rule-base><entry name=\'security\'>'
    '<rules><all/></rules></entry></rule-base></entry></vsys-name></vsys></rule-hit-count></show>': (
        'rule_hit_count.xml'
    ),
    '<show><counter><global/></counter></show>': 'counter_global.xml',
    '<show><high-availability><all/></high-availability></show>': 'ha_all.xml',
    '<show><vpn><flow/></vpn></show>': 'vpn_flow.xml',
    '<show><vpn><gateway/></vpn></show>': 'vpn_gateway.xml',
    '<request><license><info/></license></request>': 'license_info.xml',
    '<show><counter><interface>all</interface></counter></show>': 'counter_interface.xml',
    '<show><system><environmentals/></system></show>': 'environmentals.xml',
    '<show><system><resources/></system></show>': 'system_resources.xml',
}


# `type=op` commands captured on some firewall sets only (lab probes), or answered from a synthetic stand-in until
# captured, to the fixture path under FIXTURES, per set. A set missing here has no capture for the command (ruling
# R7: fw-b has no `show interface all`). Unlike the other maps, a set missing here does not fall back to fw-a's file.
PARTIAL_OP_FIXTURES = {
    '<show><interface>all</interface></show>': {'fw-a': 'fw-a-probe/interface_all.xml'},
    # Idle until lab task L10 captures `show jobs pending`.
    '<show><jobs><pending/></jobs></show>': {
        'fw-a': 'synthetic/jobs_pending_idle.xml',
        'fw-b': 'synthetic/jobs_pending_idle.xml',
    },
}


# `type=op` commands a Panorama answers, to the fixture file under FIXTURES. The answer is the synthetic one: the two
# real P1 entries plus the edge cases the lab lacks (`panorama/show_devices_connected.xml` is the unmodified capture).
PANORAMA_OP_FIXTURES = {
    '<show><devices><connected/></devices></show>': 'synthetic/panorama_show_devices_connected.xml',
}
# The `ip-address` the Panorama device list reports for each firewall set: the lab's private addresses.
PANORAMA_REPORTED_IPS = {'fw-a': '10.60.0.10', 'fw-b': '10.60.0.11'}


def panorama_op_answer(cmd: str, firewall_ips: Mapping[str, str]) -> bytes | None:
    """Return the Panorama answer to `cmd`, or None when there is none.

    The check polls the `ip-address` Panorama reports, so the device list reports each set at the address its fake
    answers on (`firewall_ips`, by set) instead of the captured lab address.
    """
    relative = PANORAMA_OP_FIXTURES.get(cmd)
    if relative is None:
        return None
    body = (FIXTURES / relative).read_bytes()
    for name, ip in firewall_ips.items():
        body = body.replace(
            f'<ip-address>{PANORAMA_REPORTED_IPS[name]}</ip-address>'.encode(),
            f'<ip-address>{ip}</ip-address>'.encode(),
        )
    return body


def set_fixture(name: str, firewall: str) -> Path:
    """Return `<firewall>/<name>` under FIXTURES, or fw-a's file of that name when the set has none.

    The two lab firewalls are identical VMs, so fw-b keeps only the files that make it a second, distinct firewall (its
    identity, and the values the docker E2E asserts for it) and answers everything else with fw-a's capture.
    """
    path = FIXTURES / firewall / name
    return path if path.exists() else FIXTURES / 'fw-a' / name


def op_fixture(cmd: str, firewall: str = 'fw-a') -> Path:
    """Return the fixture answering `type=op&cmd=<cmd>` for the given firewall set (`fw-a` or `fw-b`)."""
    return set_fixture(OP_FIXTURES[cmd], firewall)


def find_op_fixture(cmd: str, firewall: str) -> Path | None:
    """Like `op_fixture`, but also looks in PARTIAL_OP_FIXTURES, and returns None when there is no capture."""
    if cmd in OP_FIXTURES:
        return op_fixture(cmd, firewall)
    relative = PARTIAL_OP_FIXTURES.get(cmd, {}).get(firewall)
    return FIXTURES / relative if relative else None


# `type=log` queries to the fixture answering them: (response file, submit file) under FIXTURES, per set. The key is
# `(dir, query, skip)`; `nlogs` is not part of it, so a test can change the page size. `query` is None when the request
# has none. Each `forward` query is the one the threats collector sends for a watermark one below its `seqno geq`.
PROBE_SEQNO_START = 7691899338913581588
# `nlogs` of the real `probe-seqno` capture: pages p0-p18 hold 20 entries and p19 holds 5.
PROBE_SEQNO_PAGE_SIZE = 20
PROBE_SEQNO_PAGES = 20
# `seqno` of the newest log of `probe/threat_back_p0.xml`, and the watermark + 1 each set's forward threat query starts
# at. fw-b answers with fw-a's `threat_log_5m.xml` (every seqno in it is above both), but from its own seqno: a poller
# that queried with the other firewall's watermark would get no answer, so a watermark shared between firewalls fails.
BACKWARD_NEWEST_SEQNO = 7691899338913581520
THREAT_LOG_FIRST_SEQNO = {'fw-a': 7691899338913480957, 'fw-b': 7691899338913480957 - 1000}


def seqno_query(seqno: int) -> str:
    return f'(seqno geq {seqno})'


LOG_FIXTURES: dict[str, dict[tuple[str, str | None, int], tuple[str, str]]] = {
    'fw-a': {
        ('backward', None, 0): ('probe/threat_back_p0.xml', 'probe/threat_back_p0_submit.xml'),
        ('forward', seqno_query(THREAT_LOG_FIRST_SEQNO['fw-a']), 0): (
            'fw-a/threat_log_5m.xml',
            'fw-a/threat_log_5m_submit.xml',
        ),
        **{
            ('forward', seqno_query(PROBE_SEQNO_START), page * PROBE_SEQNO_PAGE_SIZE): (
                f'probe-seqno/seq_0_p{page}.xml',
                f'probe-seqno/seq_0_p{page}_submit.xml',
            )
            for page in range(PROBE_SEQNO_PAGES)
        },
    },
    'fw-b': {
        ('forward', seqno_query(THREAT_LOG_FIRST_SEQNO['fw-b']), 0): (
            'fw-a/threat_log_5m.xml',
            'fw-a/threat_log_5m_submit.xml',
        ),
    },
}


def find_log_fixture(direction: str, query: str | None, skip: int, firewall: str) -> tuple[Path, Path] | None:
    """Return the (response, submit) fixtures answering a `type=log` query for the firewall set, or None."""
    paths = LOG_FIXTURES.get(firewall, {}).get((direction, query, skip))
    return (FIXTURES / paths[0], FIXTURES / paths[1]) if paths else None


def find_report_fixture(field: str, firewall: str) -> tuple[Path, Path] | None:
    """Return the (response, submit) fixtures of the custom report aggregated by `field`, or None."""
    response = set_fixture(f'report_custom_{field}.xml', firewall)
    submit = set_fixture(f'report_custom_{field}_submit.xml', firewall)
    return (response, submit) if response.exists() and submit.exists() else None


def report_field(cmd: str) -> str | None:
    """The field a custom report submit (`type=report`) aggregates by, or None."""
    match = re.search(r'<aggregate-by><member>([^<]+)</member>', cmd)
    return match.group(1) if match else None


def log_job_fixture(params: Mapping[str, str], firewall: str) -> tuple[Path, Path] | None:
    """The (response, submit) fixtures answering the `type=log` submit with these form `params`, or None."""
    return find_log_fixture(params.get('dir', ''), params.get('query'), int(params.get('skip', '0')), firewall)


def report_job_fixture(params: Mapping[str, str], firewall: str) -> tuple[Path, Path] | None:
    """The (response, submit) fixtures answering the `type=report` submit with these form `params`, or None."""
    field = report_field(params.get('cmd', ''))
    return find_report_fixture(field, firewall) if field else None


def submit_job_id(submit: bytes) -> str | None:
    """The job id a job submit answer announces, or None."""
    match = re.search(rb'<job>(\d+)</job>', submit)
    return match.group(1).decode() if match else None
