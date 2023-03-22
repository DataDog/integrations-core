# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_METRICS, TRAFFIC_SERVER_VERSION

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, instance, dd_run_check):
    # type: (AggregatorStub, Callable[[AgentCheck, bool], None], Dict[str, Any]) -> None

    check = TrafficServerCheck('traffic_server', {}, [instance])
    traffic_server_tags = instance.get('tags')
    dd_run_check(check)

    for metric_name in EXPECTED_METRICS:
        aggregator.assert_metric(
            metric_name,
            at_least=1,
        )
        for tag in traffic_server_tags:
            aggregator.assert_metric_has_tag(metric_name, tag)
    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK, tags=traffic_server_tags)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_cant_reach_url(aggregator, instance_bad_url, dd_run_check):
    # type: (AggregatorStub, Callable[[AgentCheck, bool], None], Dict[str, Any]) -> None

    check = TrafficServerCheck('traffic_server', {}, [instance_bad_url])
    traffic_server_tags = instance_bad_url.get('tags')

    with pytest.raises(
        Exception, match='404 Client Error: Not Found on Accelerator for url: http://localhost:8080/_statss'
    ):
        dd_run_check(check)

    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.CRITICAL, tags=traffic_server_tags)
    aggregator.assert_all_metrics_covered()


def test_invalid_config(instance_no_url):

    with pytest.raises(Exception, match='Must specify a traffic_server_url'):
        TrafficServerCheck('traffic_server', {}, [instance_no_url])


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
