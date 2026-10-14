# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.pan_firewall.collectors.jobs import JOBS_PENDING_CMD, parse_busy_jobs
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_IP, STUBS, SYNTHETIC
from ..fake_panos import FAILURES, NO_CAPTURE
from ..helpers import can_connect_by_ip, new_check, register_stubs, stub_runs


def jobs_response(name):
    return 200, (SYNTHETIC / name).read_bytes()


@pytest.mark.parametrize('status', ['ACT', 'PEND'])
def test_running_or_queued_commits_and_content_updates_are_busy(status):
    # The real lab entries, one of each job type, all marked running or queued.
    root = parse_response((SYNTHETIC / 'jobs_all.xml').read_bytes())
    for job in root.iter('job'):
        job.find('status').text = status

    assert parse_busy_jobs(root) == [
        ('WildFire', '2167'),
        ('Antivirus', '2140'),
        ('Content', '2018'),
        ('Commit', '7'),
        ('AutoCom', '2'),
    ]


@pytest.mark.parametrize(
    'name',
    [
        pytest.param('jobs_all.xml', id='finished-jobs-of-every-type'),
        # No report job type was seen in the lab; Downld and IoT are the real types that never pause collection.
        pytest.param('jobs_pending_not_busy.xml', id='running-downld-and-iot'),
        # A running report job (the type name is hand-written, see the fixture) is not one of the busy types.
        pytest.param('jobs_pending_report_act.xml', id='running-report'),
    ],
)
def test_jobs_that_do_not_pause_collection(name):
    assert parse_busy_jobs(parse_response((SYNTHETIC / name).read_bytes())) == []


class Firewall:
    """fw-a with its identity cached and the stub collectors due, run at chosen times of a fake clock."""

    def __init__(self, dd_run_check, aggregator, fake_panos, caplog, monkeypatch, clock):
        self.clock = clock
        self.check = new_check()
        dd_run_check(self.check)
        register_stubs(monkeypatch)
        self.dd_run_check = dd_run_check
        self.aggregator = aggregator
        self.fake_panos = fake_panos
        self.caplog = caplog
        self.start = self.clock.now

    def answer_jobs(self, answer):
        self.fake_panos.answer_op(FW_A_IP, JOBS_PENDING_CMD, answer)

    def run_at(self, seconds):
        """Run the check `seconds` after the first run; return the collectors that ran and the warnings logged."""
        self.clock.now = self.start + seconds
        self.aggregator.reset()
        self.caplog.clear()
        self.dd_run_check(self.check)
        ran = {name for _, name in stub_runs(self.aggregator)}
        warnings = [r.getMessage() for r in self.caplog.records if r.levelno == logging.WARNING]
        return ran, warnings


@pytest.fixture
def firewall(dd_run_check, aggregator, fake_panos, caplog, monkeypatch, schedule_clock):
    caplog.set_level(logging.DEBUG)
    return Firewall(dd_run_check, aggregator, fake_panos, caplog, monkeypatch, schedule_clock)


def test_not_busy_firewall_is_checked_first_then_collected(firewall, fake_panos):
    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    calls_before = len(fake_panos.calls)

    assert firewall.run_at(0) == (set(STUBS), [])
    # The stubs make no call: the one call of the run is the jobs check.
    assert [c.cmd for c in fake_panos.calls[calls_before:]] == [JOBS_PENDING_CMD]


def test_busy_firewall_is_not_collected_and_its_collectors_stay_due(firewall, aggregator, caplog):
    firewall.answer_jobs(jobs_response('jobs_pending_commit_act.xml'))

    assert firewall.run_at(0) == (set(), [])
    # The firewall answered the jobs check.
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}
    assert f'{FW_A_IP}: Commit job 7 in progress, skipping collection this run' in caplog.text

    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    # Nothing was marked as run, so every collector is due on the next run, before its interval.
    assert firewall.run_at(60) == (set(STUBS), [])


def test_jobs_check_error_collects_anyway_and_warns_once_per_episode(firewall):
    warning = (
        f'{FW_A_IP}: cannot check for a commit or content update in progress, collecting anyway: '
        'PAN-OS API error 400: no capture for this command'
    )
    firewall.answer_jobs((200, NO_CAPTURE))

    assert firewall.run_at(0) == (set(STUBS), [warning])
    assert firewall.run_at(120) == ({'bgp', 'dataplane'}, [])
    # An answer ends the episode; the next error starts a new one.
    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    assert firewall.run_at(240) == ({'bgp', 'dataplane', 'interfaces', 'system_resources'}, [])
    firewall.answer_jobs((200, NO_CAPTURE))
    assert firewall.run_at(360) == ({'bgp', 'dataplane'}, [warning])


@pytest.mark.parametrize(
    'failure, reason',
    [
        pytest.param('refused', 'connection refused', id='refused'),
        pytest.param('timeout', 'timed out', id='timeout'),
    ],
)
def test_jobs_check_unreachable_cuts_off_the_run(firewall, aggregator, fake_panos, failure, reason):
    firewall.answer_jobs(FAILURES[failure])
    calls_before = len(fake_panos.calls)

    ran, warnings = firewall.run_at(0)

    assert ran == set()
    assert warnings == [
        f'{FW_A_IP}: could not reach the firewall ({reason}) during jobs; skipped for this run: {", ".join(STUBS)}'
    ]
    assert [c.cmd for c in fake_panos.calls[calls_before:]] == [JOBS_PENDING_CMD]
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 0}

    fake_panos.recover(FW_A_IP)
    assert firewall.run_at(60) == (set(STUBS), [])


def test_busy_for_ten_minutes_collects_anyway_with_one_warning(firewall):
    warning = f'{FW_A_IP}: Commit job 7 still in progress after 600s of skipping; collecting anyway'
    firewall.answer_jobs(jobs_response('jobs_pending_commit_act.xml'))

    for seconds in range(0, 600, 60):
        assert firewall.run_at(seconds) == (set(), []), seconds
    assert firewall.run_at(600) == (set(STUBS), [warning])
    # The job is still listed: the collectors keep their own intervals, with no new warning.
    assert firewall.run_at(660) == (set(), [])
    assert firewall.run_at(720) == ({'bgp', 'dataplane'}, [])
    assert firewall.run_at(780) == ({'interfaces', 'system_resources'}, [])


def test_idle_answer_restarts_the_ten_minute_window(firewall):
    firewall.answer_jobs(jobs_response('jobs_pending_commit_act.xml'))
    for seconds in range(0, 360, 60):
        assert firewall.run_at(seconds) == (set(), []), seconds
    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    assert firewall.run_at(360) == (set(STUBS), [])

    # A new busy period, from the next run with a due collector.
    firewall.answer_jobs(jobs_response('jobs_pending_content_pend.xml'))
    for seconds in range(480, 1080, 60):
        assert firewall.run_at(seconds) == (set(), []), seconds
    ran, warnings = firewall.run_at(1080)
    assert ran == set(STUBS)
    assert warnings == [f'{FW_A_IP}: Content job 2018 still in progress after 600s of skipping; collecting anyway']
