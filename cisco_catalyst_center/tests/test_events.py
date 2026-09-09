# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Assurance event polling.

The DevNet sandbox reports zero assurance events in every device family over any window it will
accept, so there is no captured recording of a populated response. What *is* captured is the shape
of the endpoint's contract -- the empty envelope and its rejection messages -- and the records used
here are built on that shape from the ``Event`` schema in Cisco's published AssuranceEvents spec.

That split is the one ``tests/common.py`` describes for wireless: the field names are trusted
because they come from the schema, the values are not, and nothing here asserts that a value
resembles what a real appliance would report.

The window arithmetic is tested through the check rather than the collector, because the collector
deliberately does not own it. Consecutive non-overlapping windows are the only thing stopping an
event from being counted on every cycle, and that logic lives in the check.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_events
from datadog_checks.cisco_catalyst_center.constants import EVENT_DEVICE_FAMILY_GROUPS, EVENT_WINDOW_MAX_SECONDS

from .common import load_captured, metric_values
from .conftest import ScriptedHttp

# One hour, in the epoch milliseconds the endpoint expects.
WINDOW_START = 1_755_000_000_000
WINDOW_END = 1_755_003_600_000

#: Keys taken from the ``Event`` schema. Only the fields the breakdown groups on are present,
#: because they are the only ones the collector reads.
EVENTS: list[dict[str, Any]] = [
    {
        'id': 'e1',
        'severity': 1,
        'name': 'WLC Unreachable',
        'deviceFamily': 'Wireless Controller',
        'networkDeviceName': 'wlc-1',
    },
    {
        'id': 'e2',
        'severity': 1,
        'name': 'WLC Unreachable',
        'deviceFamily': 'Wireless Controller',
        'networkDeviceName': 'wlc-2',
    },
    {
        'id': 'e3',
        'severity': 3,
        'name': 'AP Coverage Hole',
        'deviceFamily': 'Unified AP',
        'networkDeviceName': 'ap-1',
    },
]

#: One record carrying the fields the Datadog event body is assembled from. `timestamp` is epoch
#: milliseconds, as the appliance reports it.
DETAILED_EVENT: dict[str, Any] = {
    'id': 'e9',
    'severity': 0,
    'name': 'AP Disconnected',
    'deviceFamily': 'Unified AP',
    'networkDeviceName': 'ap-7',
    'siteHierarchy': 'Global/US/Building-1',
    'ssid': 'corp-wifi',
    'timestamp': 1_755_001_234_567,
    'reasonDescription': 'AP lost connection to WLC',
    'failureCategory': 'AP_CONNECTIVITY',
    'clientMac': 'aa:bb:cc:dd:ee:ff',
}


def _check(instance: InstanceType) -> CiscoCatalystCenterCheck:
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance: InstanceType, script: list[Any]) -> CatalystCenterClient:
    return CatalystCenterClient(instance, http=ScriptedHttp(script))


def _window(check: CiscoCatalystCenterCheck) -> tuple[int, int]:
    """The window the check would poll next, asserting that there is one to poll."""
    window = check._event_window()
    assert window is not None
    return window


def _page(records: list[dict[str, Any]], total: int) -> dict[str, Any]:
    """An assuranceEvents envelope. ``page.count`` is the collection total, not the page size."""
    return {'response': records, 'version': '1.0', 'page': {'limit': 20, 'offset': 1, 'count': total}}


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Freeze the clock the window arithmetic reads, and return a way to advance it.

    Time is a system boundary, and here it is the input under test. Two calls landing in the same
    millisecond are indistinguishable from a cycle whose window came out empty, so a test on the
    real clock would be asserting on how fast it happened to run.
    """
    current = {'seconds': 1_755_000_000.0}
    monkeypatch.setattr('datadog_checks.cisco_catalyst_center.check.time.time', lambda: current['seconds'])

    def advance(seconds: float) -> None:
        current['seconds'] += seconds

    return advance


# -- the request contract ---------------------------------------------------------------


def test_collect_events_asks_for_every_device_family_group(instance: InstanceType) -> None:
    # deviceFamily is mandatory and the endpoint refuses to mix its four groups in one request
    # (errorCode 2600), so a sweep that skipped a group would never see its events at all.
    client = _client(instance, [])

    collect_events(_check(instance), client, WINDOW_START, WINDOW_END)

    asked = [request['params']['deviceFamily'] for request in client.http.requests]
    assert asked == [list(group) for group in EVENT_DEVICE_FAMILY_GROUPS]


def test_collect_events_asks_for_the_window_it_was_given(instance: InstanceType) -> None:
    client = _client(instance, [])

    collect_events(_check(instance), client, WINDOW_START, WINDOW_END)

    params = client.http.requests[0]['params']
    assert (params['startTime'], params['endTime']) == (WINDOW_START, WINDOW_END)


# -- what gets emitted ------------------------------------------------------------------


def test_collect_events_given_no_events_emits_a_total_of_zero(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # Zero events is the healthy steady state and a real measurement, so it is reported rather than
    # left as a gap. One submission per family group.
    client = _client(instance, [load_captured('data_assurance_events_empty')])

    collect_events(_check(instance), client, WINDOW_START, WINDOW_END)

    assert metric_values(aggregator, 'cisco_catalyst_center.event.total.count') == [0, 0, 0, 0]


def test_collect_events_counts_by_severity_and_event_name(aggregator: AggregatorStub, instance: InstanceType) -> None:
    collect_events(_check(instance), _client(instance, [_page(EVENTS, 3)]), WINDOW_START, WINDOW_END)

    assert metric_values(aggregator, 'cisco_catalyst_center.event.count', 'severity:1') == [2]
    assert metric_values(aggregator, 'cisco_catalyst_center.event.count', 'event_name:AP Coverage Hole') == [1]


def test_collect_events_submits_counts_rather_than_gauges(aggregator: AggregatorStub, instance: InstanceType) -> None:
    # Events are a delta over a window, not a level. A gauge would report only the most recent
    # window and would not sum across the timeframe a dashboard is showing.
    collect_events(_check(instance), _client(instance, [_page(EVENTS, 3)]), WINDOW_START, WINDOW_END)

    aggregator.assert_metric('cisco_catalyst_center.event.total.count', metric_type=aggregator.COUNT)
    aggregator.assert_metric('cisco_catalyst_center.event.count', metric_type=aggregator.COUNT)


def test_collect_events_given_a_truncated_sweep_reports_the_appliance_total(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The page budget can cut a sweep short during an event storm. Counting the records that
    # arrived would report a number that reads healthy while being arbitrarily low, so the total
    # comes from page.count instead.
    collect_events(_check(instance), _client(instance, [_page(EVENTS, 4096)]), WINDOW_START, WINDOW_END)

    assert metric_values(aggregator, 'cisco_catalyst_center.event.total.count')[0] == 4096


def test_collect_events_given_one_failing_group_still_collects_the_others(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # Failing the whole sweep would make the caller retry the window, double-counting whatever the
    # earlier groups already submitted. So a group that fails is skipped instead.
    failure = {'status_code': 400, 'json': load_captured('error_device_family_mandatory')}
    client = _client(instance, [failure, _page(EVENTS, 3)])

    collect_events(_check(instance), client, WINDOW_START, WINDOW_END)

    assert metric_values(aggregator, 'cisco_catalyst_center.event.count', 'severity:1') == [2]


def test_collect_events_tags_only_the_bounded_dimensions(aggregator: AggregatorStub, instance: InstanceType) -> None:
    # The same record carries clientMac, ipv4 and username. A tag on any of them turns one event
    # into one series, which is unbounded cardinality for a question nobody asks per client.
    records = [{**EVENTS[0], 'clientMac': 'aa:bb:cc:dd:ee:ff', 'ipv4': '10.0.0.9', 'username': 'jsmith'}]

    collect_events(_check(instance), _client(instance, [_page(records, 1)]), WINDOW_START, WINDOW_END)

    keys = {
        tag.split(':', 1)[0]
        for metric in aggregator.metrics('cisco_catalyst_center.event.count')
        for tag in metric.tags
    }
    assert keys == {'severity', 'device_family', 'event_name', 'device_name'}


# -- the Datadog events -----------------------------------------------------------------


def test_collect_events_submits_one_datadog_event_per_record(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The counts say how many; the events say which. Dropping to counts alone discards 65 of the
    # 69 fields on each record, and the diagnosis is in those fields.
    collect_events(_check(instance), _client(instance, [_page(EVENTS, 3)]), WINDOW_START, WINDOW_END)

    assert len(aggregator.events) == len(EVENTS)


def test_collect_events_titles_the_event_with_the_event_name(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    collect_events(_check(instance), _client(instance, [_page([DETAILED_EVENT], 1)]), WINDOW_START, WINDOW_END)

    assert aggregator.events[0]['msg_title'] == 'AP Disconnected'


def test_collect_events_body_carries_the_diagnosis(aggregator: AggregatorStub, instance: InstanceType) -> None:
    # These are the fields a metric dimension cannot hold: free text, and per-client.
    collect_events(_check(instance), _client(instance, [_page([DETAILED_EVENT], 1)]), WINDOW_START, WINDOW_END)

    body = aggregator.events[0]['msg_text']
    assert 'AP lost connection to WLC' in body
    assert 'aa:bb:cc:dd:ee:ff' in body


def test_collect_events_converts_the_appliance_timestamp_to_seconds(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The appliance reports epoch milliseconds. Submitting those unconverted dates every event to
    # the year 57000, which silently empties the event stream for the window being viewed.
    collect_events(_check(instance), _client(instance, [_page([DETAILED_EVENT], 1)]), WINDOW_START, WINDOW_END)

    assert aggregator.events[0]['timestamp'] == 1_755_001_234


def test_collect_events_aggregates_on_the_appliance_event_id(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # A re-polled window resubmits the same events. The appliance id is what lets the stream
    # collapse them instead of showing each one twice.
    collect_events(_check(instance), _client(instance, [_page([DETAILED_EVENT], 1)]), WINDOW_START, WINDOW_END)

    assert aggregator.events[0]['aggregation_key'] == 'e9'


@pytest.mark.parametrize(
    ('severity', 'expected'),
    [
        (0, 'error'),  # Emergency, the most severe end of the syslog scale
        (3, 'error'),  # Error
        (4, 'warning'),  # Warning
        (6, 'info'),  # Info
        (99, 'info'),  # off the documented scale: must not manufacture an alert
        (None, 'info'),  # absent
    ],
)
def test_collect_events_maps_syslog_severity_to_alert_type(
    aggregator: AggregatorStub, instance: InstanceType, severity: object, expected: str
) -> None:
    record = {**DETAILED_EVENT, 'severity': severity}

    collect_events(_check(instance), _client(instance, [_page([record], 1)]), WINDOW_START, WINDOW_END)

    assert aggregator.events[0]['alert_type'] == expected


def test_collect_events_does_not_set_a_host_on_the_event(aggregator: AggregatorStub, instance: InstanceType) -> None:
    # Catalyst Center device names are not Datadog hostnames. Setting one that does not resolve
    # invents a host in the infrastructure list, so the device travels as a tag instead.
    collect_events(_check(instance), _client(instance, [_page([DETAILED_EVENT], 1)]), WINDOW_START, WINDOW_END)

    assert not aggregator.events[0].get('host')


def test_collect_events_given_no_timestamp_falls_back_to_the_window_end(
    aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The latest moment the event could have happened, and it keeps the event inside the window a
    # user is looking at rather than at the epoch.
    record = {key: value for key, value in DETAILED_EVENT.items() if key != 'timestamp'}

    collect_events(_check(instance), _client(instance, [_page([record], 1)]), WINDOW_START, WINDOW_END)

    assert aggregator.events[0]['timestamp'] == WINDOW_END // 1000


# -- the window cursor ------------------------------------------------------------------


def test_event_window_given_a_previous_cycle_starts_where_it_ended(
    instance: InstanceType, clock: Callable[[float], None]
) -> None:
    # Overlapping windows are the one failure that corrupts the metric invisibly: every event in
    # the overlap is counted twice, and nothing in the data says so.
    check = _check(instance)

    _, first_end = _window(check)
    check._events_polled_through = first_end
    clock(60)
    second_start, _ = _window(check)

    assert second_start == first_end


def test_event_window_given_a_long_outage_clamps_to_the_widest_accepted_window(
    instance: InstanceType, clock: Callable[[float], None]
) -> None:
    # An Agent restarted after a long stop resumes from a cursor the endpoint will not accept: a
    # window wider than seven days answers errorCode 14005 and so collects nothing at all.
    check = _check(instance)
    check._events_polled_through = 1_000  # epoch milliseconds, so somewhere in 1970

    start, end = _window(check)

    assert end - start == EVENT_WINDOW_MAX_SECONDS * 1000


def test_event_window_given_a_cursor_in_the_future_skips_the_cycle(
    instance: InstanceType, clock: Callable[[float], None]
) -> None:
    # An inverted window is rejected outright, and an empty one has nothing to report.
    check = _check(instance)
    check._events_polled_through = 4_000_000_000_000  # year 2096

    assert check._event_window() is None


def test_event_window_given_a_configured_lookback_uses_it_for_the_first_cycle(
    instance: InstanceType, clock: Callable[[float], None]
) -> None:
    instance['events_initial_lookback_minutes'] = 60
    check = _check(instance)

    start, end = _window(check)

    assert end - start == 60 * 60 * 1000
