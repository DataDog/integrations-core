# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Check-level tests: the wiring from a configured instance through to submissions."""

from __future__ import annotations

from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.constants import (
    ASSURANCE_EVENTS_ENDPOINT,
    CLIENT_HEALTH_ENDPOINT,
    INTENT_INTERFACES_ENDPOINT,
    NETWORK_DEVICES_ENDPOINT,
    NETWORK_HEALTH_ENDPOINT,
    SITE_HEALTH_SUMMARIES_ENDPOINT,
)
from datadog_checks.dev.utils import get_metadata_metrics

from .common import ScriptedHttp, ViewRoutedHttp, load_captured


def _serve(check: CiscoCatalystCenterCheck, payload) -> None:
    """Point the check's client at a scripted HTTP layer.

    `AgentCheck.http` is read-only, so the swap happens one level down on the client, which is
    also the more honest boundary: everything above the socket still runs.
    """
    check.client.http = ScriptedHttp([payload])


def test_check_given_reachable_appliance_reports_collection_success(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    _serve(check, load_captured('data_network_devices'))

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.collection.success', value=1)
    aggregator.assert_metric('cisco_catalyst_center.device.count', value=4)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_check_given_configured_tags_applies_them_to_metrics(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # `tags` is a standard instance option every integration is expected to honour. Generic tag
    # names such as `env` are deliberately avoided: the harness forbids a check from emitting
    # them, since unified service tagging owns them.
    instance['tags'] = ['owner:netops', 'lab:devnet']
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    _serve(check, load_captured('data_network_devices'))

    dd_run_check(check)

    aggregator.assert_metric_has_tags('cisco_catalyst_center.device.health', ['owner:netops', 'lab:devnet'])


@pytest.mark.parametrize(
    'error_fixture',
    [
        # A soft 200 is the nastiest case: the HTTP status is fine and only the body says otherwise.
        'intent_application_health_missing_param',
        'error_route_not_found',
    ],
)
def test_check_given_api_error_reports_collection_failure(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    check: CiscoCatalystCenterCheck,
    error_fixture: str,
) -> None:
    _serve(check, load_captured(error_fixture))

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.collection.success', value=0)
    aggregator.assert_metric('cisco_catalyst_center.device.health', count=0)


def test_check_given_one_failing_collector_still_emits_the_others(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    # Devices succeed, then site health fails. Losing one domain must not cost the rest of the
    # cycle -- otherwise an unreachable corner of the API blinds the whole integration. Routing by
    # path, rather than a fixed-position script, ties the failure to site health specifically, so
    # the test still targets the right collector if another one's request count changes.
    failure = {'status_code': 500, 'json': {}}
    check.client.http = ViewRoutedHttp(
        by_view={'configuration': {'response': []}, 'statistics': {'response': []}},
        by_path={
            NETWORK_DEVICES_ENDPOINT: load_captured('data_network_devices'),
            '/stack': {'response': {}},
            INTENT_INTERFACES_ENDPOINT: {'response': []},
            SITE_HEALTH_SUMMARIES_ENDPOINT: failure,
            NETWORK_HEALTH_ENDPOINT: {},
            CLIENT_HEALTH_ENDPOINT: {'response': []},
        },
    )

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=4)
    aggregator.assert_metric('cisco_catalyst_center.collection.success', value=0)


def test_check_given_two_cycles_polls_consecutive_windows(
    dd_run_check: Callable[..., None], instance: InstanceType, clock: Callable[[float], None]
) -> None:
    # Only the events collector matters here; everything else is switched off so the scripted
    # HTTP responses don't have to account for calls this test has no opinion on.
    instance.update(
        collect_stacks=False,
        collect_interfaces=False,
        collect_site_health=False,
        collect_client_experience=False,
        collect_events=True,
    )
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    empty_list = {'response': [], 'version': '1.0'}
    empty_events_page = {'response': [], 'version': '1.0', 'page': {'limit': 20, 'offset': 1, 'count': 0}}
    # Per cycle: devices, network health, client health, then one call per event device-family group.
    one_cycle = [empty_list, empty_list, empty_list, *[empty_events_page] * 4]
    check.client.http = ScriptedHttp([*one_cycle, *one_cycle])

    dd_run_check(check)
    # Real time barely moves between two calls this fast; without a frozen, advanced clock the
    # second cycle's window can collide with the first's and get skipped as an inverted window,
    # which would falsely look identical to consecutive windows never being asserted at all.
    clock(60)
    dd_run_check(check)

    event_requests = [r for r in check.client.http.requests if r['url'].endswith(ASSURANCE_EVENTS_ENDPOINT)]
    first_cycle_ends = {r['params']['endTime'] for r in event_requests[:4]}
    second_cycle_starts = {r['params']['startTime'] for r in event_requests[4:]}
    assert first_cycle_ends == second_cycle_starts, 'second cycle must resume exactly where the first one ended'


#: Issue records as the second cycle sees them relative to the first. Only the two fields the
#: reporting decision reads are present.
STILL_OPEN = {'issueId': 'issue-1', 'mostRecentOccurredTime': 1_700_000_000_000}
RECURRED = dict(STILL_OPEN, mostRecentOccurredTime=1_700_000_600_000)
SURFACED_LATE = {'issueId': 'issue-2', 'mostRecentOccurredTime': 1_699_999_000_000}
NO_TIMESTAMP = {'issueId': 'issue-3'}


@pytest.mark.parametrize(
    'first_cycle, second_cycle, expected_events',
    [
        pytest.param([STILL_OPEN], [STILL_OPEN], 1, id='still-open-issue-is-reported-once'),
        pytest.param([STILL_OPEN], [RECURRED], 2, id='recurrence-is-reported-again'),
        # Detection can lag occurrence by a different amount for each issue type, so an issue can
        # first appear after a newer one was already reported.
        pytest.param([STILL_OPEN], [STILL_OPEN, SURFACED_LATE], 2, id='issue-surfacing-after-a-newer-one'),
        pytest.param([NO_TIMESTAMP], [NO_TIMESTAMP], 1, id='issue-without-a-timestamp-is-reported-once'),
    ],
)
def test_check_given_two_cycles_reports_each_issue_occurrence_once(
    dd_run_check, aggregator, instance, first_cycle, second_cycle, expected_events
):
    # The check carries what it reported from one cycle into the next, so an issue that stays open
    # is one event rather than one per cycle, while a new occurrence still gets its own.
    instance.update(
        collect_stacks=False,
        collect_interfaces=False,
        collect_site_health=False,
        collect_client_experience=False,
        collect_assurance_issues=True,
    )
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    empty_list = {'response': [], 'version': '1.0'}

    def one_cycle(issues):
        # Per cycle: devices, network health, client health, then assurance issues.
        return [empty_list, empty_list, empty_list, {'response': issues, 'version': '1.0'}]

    check.client.http = ScriptedHttp([*one_cycle(first_cycle), *one_cycle(second_cycle)])

    dd_run_check(check)
    dd_run_check(check)

    assert len(aggregator.events) == expected_events
