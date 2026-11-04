# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.jobs import BusyJob
from datadog_checks.pan_firewall.constants import COLLECTORS
from datadog_checks.pan_firewall.scheduler import BusyGate, FirewallSchedule, Result

from .common import FW_A_IP
from .helpers import FakeClock, logged

pytestmark = pytest.mark.unit


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def schedule(clock):
    return FirewallSchedule(clock)


def test_everything_is_due_on_the_first_call(schedule, clock):
    assert schedule.due(COLLECTORS, clock.now) == list(COLLECTORS)


def test_disabled_collector_is_never_due(schedule, clock):
    enabled = [name for name in COLLECTORS if name != 'ospf']

    assert 'ospf' not in schedule.due(enabled, clock.now)
    clock.now += 86400 * 2
    assert 'ospf' not in schedule.due(enabled, clock.now)


def test_identity_metadata_is_forced_while_identity_is_missing(schedule, clock):
    # Forced even where it is not among the enabled collectors.
    enabled = ['bgp']
    schedule.mark_run(schedule.due(COLLECTORS, clock.now), clock.now)

    assert schedule.due(enabled, clock.now) == []
    assert schedule.due(enabled, clock.now, identity_missing=True) == ['identity_metadata']


@pytest.mark.parametrize(
    'name, result, elapsed, is_due',
    [
        # `licenses` runs once a day, so a retry delay shorter than its interval shows. A collector that ran is due
        # `DUE_SLACK` (5 s) before its interval.
        pytest.param('licenses', Result.RAN, 86394, False, id='ran-before-its-interval'),
        pytest.param('licenses', Result.RAN, 86395, True, id='ran-after-its-interval'),
        pytest.param('licenses', Result.FAILED, 299, False, id='failed-before-the-retry-delay'),
        pytest.param('licenses', Result.FAILED, 300, True, id='failed-after-the-retry-delay'),
        pytest.param('licenses', Result.UNREACHABLE, 299, False, id='unreachable-before-the-retry-delay'),
        pytest.param('licenses', Result.UNREACHABLE, 300, True, id='unreachable-after-the-retry-delay'),
        pytest.param('licenses', Result.SKIPPED, 0, True, id='skipped-stays-due'),
        # `bgp` runs every 2 minutes: a failure does not delay it to the retry delay.
        pytest.param('bgp', Result.FAILED, 120, True, id='failed-with-a-shorter-interval-keeps-it'),
    ],
)
def test_record_sets_the_timer_from_the_result(schedule, clock, name, result, elapsed, is_due):
    schedule.record({name: result}, clock.now)

    clock.now += elapsed
    assert (name in schedule.due(COLLECTORS, clock.now)) is is_due


def test_record_gives_the_jobs_check_no_timer(schedule, clock):
    schedule.record({'jobs': Result.UNREACHABLE}, clock.now)

    assert schedule.due(COLLECTORS, clock.now) == list(COLLECTORS)


COMMIT = [BusyJob('Commit', '7')]


def test_busy_gate_skips_for_ten_minutes_then_collects_with_one_warning():
    log = mock.Mock()
    gate = BusyGate(log, FW_A_IP)

    assert [gate.skip(COMMIT, now) for now in (0, 599, 600, 660)] == [True, True, False, False]
    assert logged(log.warning) == [
        f'{FW_A_IP}: Commit job 7 still in progress after 600s of skipping; collecting anyway'
    ]


def test_busy_gate_idle_answer_starts_a_new_window_with_its_own_warning():
    log = mock.Mock()
    gate = BusyGate(log, FW_A_IP)
    assert [gate.skip(COMMIT, now) for now in (0, 600)] == [True, False]
    gate.skip([], 700)

    assert [gate.skip(COMMIT, now) for now in (800, 1399, 1400)] == [True, True, False]
    assert len(logged(log.warning)) == 2
