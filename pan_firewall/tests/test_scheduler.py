# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.constants import COLLECTORS, INTERVALS
from datadog_checks.pan_firewall.scheduler import FirewallSchedule

TIER_2M = ['bgp', 'dataplane']
TIER_3M = ['interfaces', 'system_resources', 'vpn', 'ha', 'rule_hits', 'global_counters', 'ospf']
TIER_5M = ['environment', 'threats']
TIER_30M = ['disk', 'identity_metadata', 'reports']


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def schedule(clock):
    return FirewallSchedule(clock)


def run_due(schedule, enabled=COLLECTORS, **kwargs):
    names = schedule.due(enabled, **kwargs)
    schedule.mark_run(names)
    return names


def test_intervals_match_the_published_schedule():
    assert INTERVALS == {
        **dict.fromkeys(TIER_2M, 120),
        **dict.fromkeys(TIER_3M, 180),
        **dict.fromkeys(TIER_5M, 300),
        **dict.fromkeys(TIER_30M, 1800),
        'licenses': 86400,
    }
    assert COLLECTORS == tuple(INTERVALS)


def test_everything_is_due_on_the_first_call(schedule):
    assert schedule.due(COLLECTORS) == list(COLLECTORS)


@pytest.mark.parametrize(
    'elapsed, expected',
    [
        (60, []),
        (120, TIER_2M),
        (180, TIER_2M + TIER_3M),
        (300, TIER_2M + TIER_3M + TIER_5M),
        (1800, TIER_2M + TIER_3M + TIER_5M + TIER_30M),
        (86400, list(COLLECTORS)),
    ],
)
def test_collectors_are_due_after_their_interval(schedule, clock, elapsed, expected):
    run_due(schedule)

    clock.now += elapsed
    assert schedule.due(COLLECTORS) == expected


def test_licenses_are_due_only_after_a_day(schedule, clock):
    run_due(schedule)

    clock.now += 86399
    assert 'licenses' not in schedule.due(COLLECTORS)
    clock.now += 1
    assert 'licenses' in schedule.due(COLLECTORS)


def test_tiers_repeat_on_their_own_cadence(schedule, clock):
    run_due(schedule)

    clock.now += 120
    assert run_due(schedule) == TIER_2M
    clock.now += 60
    assert run_due(schedule) == TIER_3M
    clock.now += 60
    assert run_due(schedule) == TIER_2M


def test_disabled_collector_is_never_due(schedule, clock):
    enabled = [name for name in COLLECTORS if name != 'ospf']

    assert 'ospf' not in schedule.due(enabled)
    clock.now += 86400 * 2
    assert 'ospf' not in schedule.due(enabled)


def test_collector_marked_after_a_failure_is_pushed_forward(schedule, clock):
    # `mark_run` is called for collectors that ran, whether they succeeded or not.
    schedule.mark_run(['bgp'])

    clock.now += 119
    assert 'bgp' not in schedule.due(['bgp'])
    clock.now += 1
    assert schedule.due(['bgp']) == ['bgp']


def test_skipped_cycle_leaves_collectors_due(schedule, clock):
    first = schedule.due(COLLECTORS)
    clock.now += 600

    assert schedule.due(COLLECTORS) == first
    assert schedule.due(COLLECTORS) == first


@pytest.mark.parametrize('enabled', [COLLECTORS, ['bgp']])
def test_identity_metadata_is_forced_while_identity_is_missing(schedule, enabled):
    run_due(schedule)

    assert schedule.due(enabled) == []
    assert schedule.due(enabled, identity_missing=True) == ['identity_metadata']
