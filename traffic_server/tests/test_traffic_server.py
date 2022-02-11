# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_COUNT_METRICS, EXPECTED_GAUGE_METRICS, TRAFFIC_SERVER_VERSION

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, instance, dd_run_check):
    # type: (AggregatorStub, Callable[[AgentCheck, bool], None], Dict[str, Any]) -> None

    check = TrafficServerCheck('traffic_server', {}, [instance])
    traffic_server_tags = instance.get('tags')
    dd_run_check(check)

    for metric_name in EXPECTED_COUNT_METRICS:
        aggregator.assert_metric(
            metric_name, count=1, tags=traffic_server_tags, metric_type=AggregatorStub.MONOTONIC_COUNT
        )

    for metric_name in EXPECTED_GAUGE_METRICS:
        aggregator.assert_metric(metric_name, count=1, tags=traffic_server_tags, metric_type=AggregatorStub.GAUGE)

    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)
    aggregator.assert_all_metrics_covered()
    # from datadog_checks.dev.utils import get_metadata_metrics
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_version_metadata(instance, dd_run_check, datadog_agent):
    check = TrafficServerCheck('traffic_server', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    raw_version = TRAFFIC_SERVER_VERSION

    major, minor, patch = raw_version.split(".")

    version_metadata = {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": raw_version,
    }

    datadog_agent.assert_metadata("test:123", version_metadata)
