# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.jobs import JOBS_PENDING_CMD, BusyJob, parse_busy_jobs
from datadog_checks.pan_firewall.scheduler import BusyGate
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_IP, STUBS, SYNTHETIC
from ..fake_panos import FAILURES, NO_CAPTURE
from ..helpers import can_connect_by_ip, logged, new_check, register_stubs, stub_runs

# The poller tests run with the stub collectors they register.
pytestmark = [pytest.mark.unit, pytest.mark.stub_collectors]

COMMIT = [BusyJob('Commit', '7')]
IDLE = (200, b'<response status="success"><result/></response>')
COMMIT_RUNNING = (
    200,
    b'<response status="success"><result>'
    b'<job><id>7</id><type>Commit</type><status>ACT</status></job>'
    b'</result></response>',
)


@pytest.mark.parametrize(
    'status, busy',
    [
        pytest.param('ACT', True, id='running'),
        pytest.param('PEND', True, id='queued'),
        pytest.param('FIN', False, id='finished'),
    ],
)
def test_busy_job_types(status, busy):
    # The lab's real entries, one of each job type; Downld and IoT never pause collection.
    root = parse_response((SYNTHETIC / 'jobs_all.xml').read_bytes())
    for job in root.iter('job'):
        job.find('status').text = status

    expected = [('WildFire', '2167'), ('Antivirus', '2140'), ('Content', '2018'), ('Commit', '7'), ('AutoCom', '2')]
    assert parse_busy_jobs(root) == (expected if busy else [])


def test_busy_gate_skips_for_ten_minutes_then_collects_with_one_warning():
    log = mock.Mock()
    gate = BusyGate(log, FW_A_IP)

    assert [gate.skip(COMMIT, now) for now in (0, 599, 600, 660)] == [True, True, False, False]
    assert logged(log.warning) == [
        f'{FW_A_IP}: Commit job 7 still in progress after 600s of skipping; collecting anyway'
    ]


def test_busy_gate_idle_answer_starts_a_new_window():
    gate = BusyGate(mock.Mock(), FW_A_IP)
    gate.skip(COMMIT, 0)
    gate.skip([], 300)

    assert [gate.skip(COMMIT, now) for now in (700, 1299, 1300)] == [True, True, False]


@pytest.fixture
def run_at(dd_run_check, aggregator, monkeypatch, schedule_clock):
    """Run fw-a, its identity cached and the stub collectors due, `seconds` after a first run; return the collectors
    that ran."""
    check = new_check()
    dd_run_check(check)
    register_stubs(monkeypatch)
    start = schedule_clock.now

    def run(seconds):
        schedule_clock.now = start + seconds
        aggregator.reset()
        dd_run_check(check)
        return {name for _, name in stub_runs(aggregator)}

    return run


def test_busy_firewall_is_not_collected_and_its_collectors_stay_due(run_at, aggregator, fake_panos):
    fake_panos.answer_op(FW_A_IP, JOBS_PENDING_CMD, COMMIT_RUNNING)
    assert run_at(0) == set()
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}

    fake_panos.answer_op(FW_A_IP, JOBS_PENDING_CMD, IDLE)
    assert run_at(60) == set(STUBS)


def test_jobs_check_error_collects_anyway_and_warns_on_every_run(run_at, fake_panos, caplog):
    fake_panos.answer_op(FW_A_IP, JOBS_PENDING_CMD, (200, NO_CAPTURE))

    assert run_at(0) == set(STUBS)
    assert run_at(120) == {'bgp', 'dataplane'}
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert all(w.startswith(f'{FW_A_IP}: cannot check for a commit or content update in progress') for w in warnings)


def test_jobs_check_unreachable_cuts_off_the_run(run_at, aggregator, fake_panos):
    fake_panos.answer_op(FW_A_IP, JOBS_PENDING_CMD, FAILURES['refused'])
    calls_before = len(fake_panos.calls)

    assert run_at(0) == set()
    assert [c.cmd for c in fake_panos.calls[calls_before:]] == [JOBS_PENDING_CMD]
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 0}

    fake_panos.recover(FW_A_IP)
    assert run_at(60) == set(STUBS)
