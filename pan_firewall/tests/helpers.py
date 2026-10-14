# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Helpers shared by the unit tests.

Unlike `common.py`, this module imports the check: the docker fakes import `common`, `fake_panos` and `fixture_map`
without the check installed, so none of those may import this one.
"""

import copy
from unittest import mock
from xml.etree import ElementTree as ET

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState, Sample
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import CREDENTIALS, FW_A_IP, STUBS, SYNTHETIC
from .fixture_map import op_fixture


class FakeClock:
    """A monotonic clock a test moves by setting `now`."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def load_xml(path):
    return parse_response(path.read_bytes())


def load_op(cmd, firewall='fw-a'):
    """The parsed answer of the firewall set to `type=op&cmd=<cmd>`."""
    return load_xml(op_fixture(cmd, firewall))


def interface_state(path):
    """The state the identity step builds from the `show interface all` answer at `path`."""
    root = load_xml(path)
    return FirewallState(
        interface_rows=root.findall('./result/ifnet/entry'),
        interface_map={e.findtext('name') or '': e for e in root.findall('./result/hw/entry')},
    )


def series(samples):
    """Samples keyed by (name, tags) to (value, kind); fails on a duplicate (two values for one series)."""
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def make_ctx(response=None, *, state=None, identity=None, config=None, **kwargs):
    """A `CollectContext` with mocks; the client's `op` answers `response`, a parsed root or a dict by command."""
    ctx = CollectContext(
        client=mock.Mock(),
        identity=mock.Mock() if identity is None else identity,
        state=FirewallState() if state is None else state,
        config=mock.Mock() if config is None else config,
        log=mock.Mock(),
        **kwargs,
    )
    if isinstance(response, dict):
        ctx.client.op.side_effect = lambda cmd: response[cmd]
    elif response is not None:
        ctx.client.op.return_value = response
    return ctx


def make_instance(ip=FW_A_IP, **options):
    return {'firewalls': [ip], 'firewall_credentials': copy.deepcopy(CREDENTIALS), 'tags': ['team:test'], **options}


def new_check(instance=None):
    return PanFirewallCheck('pan_firewall', {}, [instance or make_instance()])


def stub_sample(name):
    return Sample('stub', 1, (f'collector:{name}',), 'gauge')


def register_stubs(monkeypatch, **overrides):
    """Register a stub for each name in STUBS that submits `pan_firewall.stub` tagged `collector:<name>`."""
    for name in STUBS:
        monkeypatch.setitem(COLLECT_FUNCTIONS, name, overrides.get(name, lambda ctx, name=name: [stub_sample(name)]))


def stub_runs(aggregator):
    """The (device_ip, collector) pairs that submitted a stub sample."""
    runs = set()
    for metric in aggregator.metrics('pan_firewall.stub'):
        tags = dict(tag.split(':', 1) for tag in metric.tags if tag.startswith(('device_ip:', 'collector:')))
        runs.add((tags['device_ip'], tags['collector']))
    return runs


def metrics_by_ip(aggregator, name):
    """The `pan_firewall.<name>` metric of each `device_ip`."""
    return {
        next(t.split(':', 1)[1] for t in m.tags if t.startswith('device_ip:')): m
        for m in aggregator.metrics(f'pan_firewall.{name}')
    }


def can_connect_by_ip(aggregator):
    return {ip: metric.value for ip, metric in metrics_by_ip(aggregator, 'can_connect').items()}


# Threat log job answers: a job still running, and a finished one built from a real entry.
THREAT_LOG_ACT = (SYNTHETIC / 'threat_log_act.xml').read_bytes()
THREAT_LOG_CLOCK_BACK = SYNTHETIC / 'threat_log_clock_back.xml'
POLL_ENTRY = ET.parse(THREAT_LOG_CLOCK_BACK).getroot().find('result/log/logs/entry')


def log_page(seqnos, **fields):
    """A finished log job of one entry per seqno, copied from a real entry of `synthetic/threat_log_clock_back.xml`."""
    entries = []
    for seqno in seqnos:
        entry = copy.deepcopy(POLL_ENTRY)
        entry.find('seqno').text = str(seqno)
        for name, value in fields.items():
            entry.find(name).text = value
        entries.append(ET.tostring(entry, encoding='unicode'))
    return (
        '<response status="success"><result><job><status>FIN</status><id>1</id></job>'
        f'<log><logs count="{len(entries)}" progress="100">{"".join(entries)}</logs></log></result></response>'
    ).encode()
