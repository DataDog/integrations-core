# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Check-level tests: the wiring from a configured instance through to submissions."""

from __future__ import annotations

from typing import Any, Callable

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

from .common import ScriptedHttp, ViewRoutedHttp, load_captured, metric_values, with_value

# The device inventory sweep. It takes no `view` parameter, so a routed fake has to match it by path.
INVENTORY_PATH = '/dna/intent/api/v1/network-device'

#: An empty answer from the inventory sweep, for tests whose subject is not the reachability fallback.
NO_INVENTORY: dict[str, Any] = {'response': []}


def _serve(check: CiscoCatalystCenterCheck, payload) -> None:
    """Point the check's client at a scripted HTTP layer that answers the device collector with `payload`.

    `AgentCheck.http` is read-only, so the swap happens one level down on the client, which is
    also the more honest boundary: everything above the socket still runs. The inventory sweep runs
    first, so it is answered empty to let `payload` reach the device collector.
    """
    check.client.http = ScriptedHttp([NO_INVENTORY, payload])


def _core_only(instance: InstanceType) -> CiscoCatalystCenterCheck:
    """A check with every optional collector off, leaving the calls that run on every cycle."""
    instance.update(
        collect_stacks=False,
        collect_interfaces=False,
        collect_site_health=False,
        collect_client_experience=False,
    )
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _route(check: CiscoCatalystCenterCheck, devices, inventory) -> None:
    """Answer the data API's device list and the inventory sweep, and the other core calls empty."""
    check.client.http = ViewRoutedHttp(
        by_view={},
        by_path={
            NETWORK_DEVICES_ENDPOINT: devices,
            INVENTORY_PATH: inventory,
            NETWORK_HEALTH_ENDPOINT: {},
            CLIENT_HEALTH_ENDPOINT: {'response': []},
        },
    )


def _inventory_with(hostname: str, status: str):
    """The captured inventory with one device's reachability replaced."""
    inventory = load_captured('intent_network_device')
    index = next(i for i, record in enumerate(inventory['response']) if record['hostname'] == hostname)
    return with_value(inventory, f'response.{index}.reachabilityStatus', status)


def _fail_site_health(check: CiscoCatalystCenterCheck) -> None:
    """Serve a cycle in which the devices succeed and site health answers HTTP 500.

    Routing by path, rather than a fixed-position script, ties the failure to site health
    specifically, so the test still targets the right collector if another one's request count changes.
    """
    check.client.http = ViewRoutedHttp(
        by_view={'configuration': {'response': []}, 'statistics': {'response': []}},
        by_path={
            NETWORK_DEVICES_ENDPOINT: load_captured('data_network_devices'),
            INVENTORY_PATH: load_captured('intent_network_device'),
            '/stack': {'response': {}},
            INTENT_INTERFACES_ENDPOINT: {'response': []},
            SITE_HEALTH_SUMMARIES_ENDPOINT: {'status_code': 500, 'json': {}},
            NETWORK_HEALTH_ENDPOINT: {},
            CLIENT_HEALTH_ENDPOINT: {'response': []},
        },
    )


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
    # cycle -- otherwise an unreachable corner of the API blinds the whole integration.
    _fail_site_health(check)

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=4)
    aggregator.assert_metric('cisco_catalyst_center.collection.success', value=0)


def test_check_given_one_failing_collector_names_it_in_a_warning(
    dd_run_check: Callable[..., None], check: CiscoCatalystCenterCheck
) -> None:
    # A failure that reaches only the log leaves the Agent status reading OK while a domain has
    # stopped reporting -- the reservable sandbox's network health answered HTTP 500 for hours on
    # 2026-10-06 without the status changing. A warning puts the failing collector on that page.
    _fail_site_health(check)

    dd_run_check(check)

    assert [warning for warning in check.warnings if 'site health' in warning]


@pytest.mark.parametrize(
    'optional_collectors',
    [
        pytest.param({}, id='core-collectors-only'),
        # Application health fans out over a site list that fails along with everything else. A
        # sweep over no sites makes no request, so it must not count as a collector that succeeded.
        pytest.param({'collect_application_health': True}, id='with-application-health'),
    ],
)
def test_check_given_every_collector_failing_raises_and_still_reports_collection_failure(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    optional_collectors: dict[str, bool],
) -> None:
    # An unreachable appliance or a rejected login fails every call. That is an error rather than
    # a degraded cycle, and collection.success must still arrive for a monitor to alert on.
    instance.update(optional_collectors)
    check = _core_only(instance)
    check.client.http = ViewRoutedHttp(by_view={None: {'status_code': 500, 'json': {}}})

    with pytest.raises(Exception, match='Every Catalyst Center collector failed'):
        dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.collection.success', value=0)


# -- device reachability ----------------------------------------------------------------


def test_check_given_no_data_api_reachability_reports_the_inventory_status(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The data API leaves reachabilityHealthStatus null while Assurance re-scores devices: three
    # reachable switches had none for at least 38 minutes on 2026-10-06. The inventory still knew,
    # and without it a switch that loses power sends no reachability at all.
    check = _core_only(instance)
    devices = with_value(load_captured('data_network_devices'), 'response.0.reachabilityHealthStatus', None)
    _route(check, devices=devices, inventory=_inventory_with('sw1', 'Unreachable'))

    dd_run_check(check)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == [0]


@pytest.mark.parametrize(
    'devices',
    [
        pytest.param(
            with_value(load_captured('data_network_devices'), 'response.0.reachabilityHealthStatus', None),
            id='data-api-reports-none',
        ),
        pytest.param({'response': []}, id='inventory-only'),
    ],
)
def test_check_given_an_empty_inventory_reachability_reports_no_reachability(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType, devices: dict[str, Any]
):
    # The empty string is absent data from the inventory just as from the data API. Reporting it as
    # not reachable would page on a device that nothing says is down.
    check = _core_only(instance)
    _route(check, devices=devices, inventory=_inventory_with('sw1', ''))

    dd_run_check(check)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == []


def test_check_given_devices_missing_from_the_data_api_reports_their_inventory_status(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The data API drops devices while it re-indexes, and once answered with none at all right
    # after a site assignment. The inventory lists every managed device regardless.
    check = _core_only(instance)
    _route(check, devices={'response': []}, inventory=load_captured('intent_network_device'))

    dd_run_check(check)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == [1]


@pytest.mark.parametrize(
    'returned',
    [
        pytest.param(4, id='both-sources-list-every-device'),
        pytest.param(3, id='data-api-drops-one'),
        pytest.param(0, id='data-api-drops-all'),
    ],
)
def test_check_given_two_device_sources_counts_each_managed_device_once(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType, returned: int
):
    # device.count is the number of managed devices, which the data API understates whenever it
    # drops some. The inventory also lists every device the data API did return, so a device both
    # sources report must still count once.
    devices = load_captured('data_network_devices')
    devices = with_value(devices, 'response', devices['response'][:returned])
    check = _core_only(instance)
    _route(check, devices=devices, inventory=load_captured('intent_network_device'))

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.device.count', value=4)


def test_check_given_both_sources_report_reachability_prefers_the_data_api(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # The inventory fills gaps; it is not a second opinion. While the data API answers, the gauge
    # stays exactly what it was before the inventory was read.
    check = _core_only(instance)
    _route(check, devices=load_captured('data_network_devices'), inventory=_inventory_with('sw1', 'Unreachable'))

    dd_run_check(check)

    assert metric_values(aggregator, 'cisco_catalyst_center.device.reachable', 'device_name:sw1') == [1]


def test_check_given_interface_statistics_tags_device_throughput_with_the_device(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, instance: InstanceType
) -> None:
    # Throughput is rolled up per device from interface records, which carry only the device's IP
    # and UUID. Without the device record's tags, a dashboard can neither filter throughput by
    # site nor label a device by name.
    instance.update(collect_stacks=False, collect_site_health=False, collect_client_experience=False)
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    check.client.http = ViewRoutedHttp(
        by_view={
            'configuration': load_captured('data_interfaces_configuration'),
            'statistics': load_captured('data_interfaces_statistics'),
        },
        by_path={
            NETWORK_DEVICES_ENDPOINT: load_captured('data_network_devices'),
            INVENTORY_PATH: load_captured('intent_network_device'),
            INTENT_INTERFACES_ENDPOINT: {'response': []},
            NETWORK_HEALTH_ENDPOINT: {},
            CLIENT_HEALTH_ENDPOINT: {'response': []},
        },
    )

    dd_run_check(check)

    aggregator.assert_metric_has_tag('cisco_catalyst_center.device.throughput.rx', 'device_name:sw1')


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
    # Per cycle: the inventory sweep, devices, network health, client health, then one call per
    # event device-family group.
    one_cycle = [empty_list, empty_list, empty_list, empty_list, *[empty_events_page] * 4]
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
        # Per cycle: the inventory sweep, devices, network health, client health, then assurance issues.
        return [empty_list, empty_list, empty_list, empty_list, {'response': issues, 'version': '1.0'}]

    check.client.http = ScriptedHttp([*one_cycle(first_cycle), *one_cycle(second_cycle)])

    dd_run_check(check)
    dd_run_check(check)

    assert len(aggregator.events) == expected_events
