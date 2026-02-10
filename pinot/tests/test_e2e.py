# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import CONTROLLER_NAMESPACE
from .conftest import E2E_METRICS_URL

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, e2e_instance):
    """
    Test that the Pinot check collects metrics from a real Pinot QuickStart cluster.

    In QuickStart mode, all Pinot components (Controller, Server, Broker, Minion)
    run in the same JVM, so all metrics are exposed on a single JMX endpoint.
    """
    aggregator = dd_agent_check(e2e_instance, rate=True)

    # Verify service check - uses controller namespace since e2e_instance uses controller_endpoint
    aggregator.assert_service_check(f'{CONTROLLER_NAMESPACE}.openmetrics.health', ServiceCheck.OK)

    # Verify some common JVM metrics are collected
    # These should be present for any Pinot component
    jvm_metrics = [
        'pinot.controller.jvm_memory_bytes_used',
        'pinot.controller.jvm_threads_current',
    ]

    for metric in jvm_metrics:
        aggregator.assert_metric(metric, at_least=1)

    # Verify endpoint tag is present
    aggregator.assert_metric_has_tag(
        'pinot.controller.jvm_memory_bytes_used',
        f'endpoint:{E2E_METRICS_URL}',
        at_least=1,
    )

    # Verify custom tag is present
    aggregator.assert_metric_has_tag(
        'pinot.controller.jvm_memory_bytes_used',
        'test:e2e',
        at_least=1,
    )
