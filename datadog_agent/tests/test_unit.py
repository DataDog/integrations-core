# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.datadog_agent import DatadogAgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

pytestmark = pytest.mark.unit

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'telemetry.txt')


def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
):
    mock_http_response(file_path=FIXTURE_PATH)

    check = DatadogAgentCheck('datadog_agent', {}, [instance])
    dd_run_check(check)

    # Every documented metric is collected by default from the Agent's telemetry payload, and nothing else is: the
    # fixture also contains telemetry outside the default set (`transactions__success_bytes`).
    for metric in get_metadata_metrics():
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    # `endpoint` is the forwarder's intake endpoint, not the scraped URL.
    aggregator.assert_metric(
        'datadog.agent.forwarder.transactions.success.count',
        tags=[
            'domain:https://7-84-5-app.agent.datadoghq.com.',
            'endpoint:series_v3',
            'proto_version:HTTP/1.1',
            'test:tag',
        ],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
