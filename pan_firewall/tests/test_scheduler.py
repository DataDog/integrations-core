# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.constants import COLLECTORS
from datadog_checks.pan_firewall.scheduler import FirewallSchedule

from .helpers import FakeClock

TIER_2M = ['bgp', 'dataplane']
TIER_3M = ['interfaces', 'system_resources', 'vpn', 'ha', 'rule_hits', 'global_counters', 'ospf']
TIER_5M = ['environment', 'threats']
TIER_30M = ['disk', 'identity_metadata', 'reports']


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


def test_identity_metadata_is_forced_while_identity_is_missing(schedule):
    # Forced even where it is not among the enabled collectors.
    enabled = ['bgp']
    run_due(schedule)

    assert schedule.due(enabled) == []
    assert schedule.due(enabled, identity_missing=True) == ['identity_metadata']


def test_failed_collectors_are_retried_within_5_minutes(schedule, clock):
    schedule.mark_failed(COLLECTORS)

    # Collectors with a shorter interval keep it.
    clock.now += 120
    assert schedule.due(COLLECTORS) == TIER_2M
    clock.now += 179
    assert schedule.due(COLLECTORS) == TIER_2M + TIER_3M
    clock.now += 1
    assert schedule.due(COLLECTORS) == list(COLLECTORS)
