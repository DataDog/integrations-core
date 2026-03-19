# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import BROKER_NAMESPACE, CONTROLLER_NAMESPACE, MINION_NAMESPACE, SERVER_NAMESPACE

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, e2e_instance):
    """
    Test that the Pinot check collects metrics from a real Pinot QuickStart cluster.

    In QuickStart mode, all Pinot components (Controller, Server, Broker, Minion)
    run in the same JVM, so all metrics are exposed on a single JMX endpoint.
    All four component endpoints are configured to point at that shared endpoint,
    each collecting its component-specific metrics under its own namespace.
    """
    aggregator = dd_agent_check(e2e_instance, rate=True)

    for namespace in (CONTROLLER_NAMESPACE, SERVER_NAMESPACE, BROKER_NAMESPACE, MINION_NAMESPACE):
        aggregator.assert_metric(f'{namespace}.can_connect', value=1)

    metadata_metrics = get_metadata_metrics()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=False,
    )
