# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.pan_firewall.collectors.jobs import JOBS_PENDING_CMD, parse_busy_jobs
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_IP, STUBS, SYNTHETIC
from ..fake_panos import FAILURES, NO_CAPTURE
from ..helpers import can_connect_by_ip, new_check, register_stubs, stub_runs

# These tests run the poller with the stub collectors they register.
pytestmark = pytest.mark.stub_collectors


def jobs_response(name):
    return 200, (SYNTHETIC / name).read_bytes()


def pending_jobs(*jobs):
    """A `show jobs pending` answer made of the `jobs_all.xml` entries named by (id, status[, type]), in that order.

    Every other job is dropped: a pending answer that lists finished jobs is not realistic. A type is set only for a
    job type the lab never produced.
    """
    root = parse_response((SYNTHETIC / 'jobs_all.xml').read_bytes())
    result = root.find('result')
    by_id = {job.findtext('id'): job for job in result.findall('job')}
    for job in by_id.values():
        result.remove(job)
    for job_id, status, *job_type in jobs:
        job = by_id[job_id]
        job.find('status').text = status
        if job_type:
            job.find('type').text = job_type[0]
        result.append(job)
    return ET.tostring(root)


COMMIT_RUNNING = pending_jobs(('7', 'ACT'))
CONTENT_PENDING = pending_jobs(('2018', 'PEND'))
COMMIT_RUNNING_AND_CONTENT_PENDING = pending_jobs(('7', 'ACT'), ('2018', 'PEND'))
DOWNLOAD_AND_IOT_RUNNING = pending_jobs(('2166', 'ACT'), ('1350', 'ACT'))
# The type name is not from a capture: no report job was seen in `show jobs`, so it only stands for a type outside
# the busy ones.
REPORT_RUNNING = pending_jobs(('2166', 'ACT', 'Report'))


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
    'body',
    [
        pytest.param((SYNTHETIC / 'jobs_all.xml').read_bytes(), id='finished-jobs-of-every-type'),
        # No report job type was seen in the lab; Downld and IoT are the real types that never pause collection.
        pytest.param(DOWNLOAD_AND_IOT_RUNNING, id='running-downld-and-iot'),
        # A running report job is not one of the busy types.
        pytest.param(REPORT_RUNNING, id='running-report'),
    ],
)
def test_jobs_that_do_not_pause_collection(body):
    assert parse_busy_jobs(parse_response(body)) == []


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
        """Run the check `seconds` after the first run; return the collectors that ran."""
        self.clock.now = self.start + seconds
        self.aggregator.reset()
        self.caplog.clear()
        self.dd_run_check(self.check)
        return {name for _, name in stub_runs(self.aggregator)}

    def warnings(self):
        """The warnings logged by the last run."""
        return [r.getMessage() for r in self.caplog.records if r.levelno == logging.WARNING]


@pytest.fixture
def firewall(dd_run_check, aggregator, fake_panos, caplog, monkeypatch, schedule_clock):
    caplog.set_level(logging.DEBUG)
    return Firewall(dd_run_check, aggregator, fake_panos, caplog, monkeypatch, schedule_clock)


def test_not_busy_firewall_is_checked_first_then_collected(firewall, fake_panos):
    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    calls_before = len(fake_panos.calls)

    assert firewall.run_at(0) == set(STUBS)
    # The stubs make no call: the one call of the run is the jobs check.
    assert [c.cmd for c in fake_panos.calls[calls_before:]] == [JOBS_PENDING_CMD]


def test_busy_firewall_is_not_collected_and_its_collectors_stay_due(firewall, aggregator):
    firewall.answer_jobs((200, COMMIT_RUNNING))

    assert firewall.run_at(0) == set()
    # The firewall answered the jobs check.
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}

    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    # Nothing was marked as run, so every collector is due on the next run, before its interval.
    assert firewall.run_at(60) == set(STUBS)


def test_every_busy_job_is_named(firewall, caplog):
    firewall.answer_jobs((200, COMMIT_RUNNING_AND_CONTENT_PENDING))

    assert firewall.run_at(0) == set()
    assert f'{FW_A_IP}: Commit job 7, Content job 2018 in progress, skipping collection this run' in caplog.text


def test_jobs_check_error_collects_anyway_and_warns_on_every_run(firewall):
    firewall.answer_jobs((200, NO_CAPTURE))

    for seconds, collected in ((0, set(STUBS)), (120, {'bgp', 'dataplane'})):
        assert firewall.run_at(seconds) == collected
        (warning,) = firewall.warnings()
        assert warning.startswith(f'{FW_A_IP}: cannot check for a commit or content update in progress')


@pytest.mark.parametrize('failure', ['refused', 'timeout'])
def test_jobs_check_unreachable_cuts_off_the_run(firewall, aggregator, fake_panos, failure):
    firewall.answer_jobs(FAILURES[failure])
    calls_before = len(fake_panos.calls)

    assert firewall.run_at(0) == set()
    assert [c.cmd for c in fake_panos.calls[calls_before:]] == [JOBS_PENDING_CMD]
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 0}

    fake_panos.recover(FW_A_IP)
    assert firewall.run_at(60) == set(STUBS)


def test_busy_for_ten_minutes_collects_anyway_with_one_warning(firewall):
    warning = f'{FW_A_IP}: Commit job 7 still in progress after 600s of skipping; collecting anyway'
    firewall.answer_jobs((200, COMMIT_RUNNING))

    for seconds in range(0, 600, 60):
        assert (firewall.run_at(seconds), firewall.warnings()) == (set(), []), seconds
    assert (firewall.run_at(600), firewall.warnings()) == (set(STUBS), [warning])
    # The job is still listed: the collectors keep their own intervals, with no new warning.
    assert (firewall.run_at(660), firewall.warnings()) == (set(), [])
    assert (firewall.run_at(720), firewall.warnings()) == ({'bgp', 'dataplane'}, [])
    assert (firewall.run_at(780), firewall.warnings()) == ({'interfaces', 'system_resources'}, [])


def test_idle_answer_restarts_the_ten_minute_window(firewall):
    firewall.answer_jobs((200, COMMIT_RUNNING))
    for seconds in range(0, 360, 60):
        assert firewall.run_at(seconds) == set(), seconds
    firewall.answer_jobs(jobs_response('jobs_pending_idle.xml'))
    assert firewall.run_at(360) == set(STUBS)

    # A new busy period, from the next run with a due collector.
    firewall.answer_jobs((200, CONTENT_PENDING))
    for seconds in range(480, 1080, 60):
        assert firewall.run_at(seconds) == set(), seconds
    assert firewall.run_at(1080) == set(STUBS)
