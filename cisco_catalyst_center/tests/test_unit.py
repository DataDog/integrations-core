# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Check-level tests: the wiring from a configured instance through to submissions."""

from __future__ import annotations

from typing import Callable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center import CiscoCatalystCenterCheck

from .common import load_captured
from .conftest import ScriptedHttp


@pytest.fixture
def check(instance: InstanceType) -> CiscoCatalystCenterCheck:
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _serve(check: CiscoCatalystCenterCheck, payload) -> None:
    """Point the check's client at a scripted HTTP layer.

    ``AgentCheck.http`` is read-only, so the swap happens one level down on the client, which is
    also the more honest boundary: everything above the socket still runs.
    """
    check.client.http = ScriptedHttp([payload])


def test_check_given_reachable_appliance_reports_can_connect_ok(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    _serve(check, load_captured('data_network_devices'))

    dd_run_check(check)

    aggregator.assert_service_check('cisco_catalyst_center.can_connect', ServiceCheck.OK, count=1)
    aggregator.assert_metric('cisco_catalyst_center.device.count', value=4)


def test_check_given_configured_tags_applies_them_to_metrics_and_service_check(
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
    service_check = aggregator.service_checks('cisco_catalyst_center.can_connect')[0]
    assert 'owner:netops' in service_check.tags


def test_check_given_api_error_reports_can_connect_critical(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    # A soft 200 is the nastiest case: the HTTP status is fine and only the body says otherwise.
    _serve(check, load_captured('intent_application_health_missing_param'))

    dd_run_check(check)

    aggregator.assert_service_check('cisco_catalyst_center.can_connect', ServiceCheck.CRITICAL, count=1)


def test_check_given_one_failing_collector_still_emits_the_others(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    # Devices succeed, then site health fails. Losing one domain must not cost the rest of the
    # cycle -- otherwise an unreachable corner of the API blinds the whole integration.
    from .conftest import ScriptedHttp

    devices = load_captured('data_network_devices')
    failure = {'status_code': 500, 'json': {}}
    # devices, stacks (4 switches), interfaces (configuration + statistics), then site health.
    check.client.http = ScriptedHttp([devices, *[{'response': {}}] * 4, {'response': []}, {'response': []}, failure])

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=4)
    aggregator.assert_service_check('cisco_catalyst_center.can_connect', ServiceCheck.CRITICAL, count=1)


def test_check_given_api_error_emits_no_device_metrics(
    dd_run_check: Callable[..., None], aggregator: AggregatorStub, check: CiscoCatalystCenterCheck
) -> None:
    _serve(check, load_captured('error_route_not_found'))

    dd_run_check(check)

    aggregator.assert_metric('cisco_catalyst_center.device.health', count=0)
