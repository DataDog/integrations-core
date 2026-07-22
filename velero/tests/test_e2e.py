# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import OPTIONAL_METRICS, TEST_METRICS


def assert_metrics(aggregator):
    for metric, _ in TEST_METRICS.items():
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(name=metric, at_least=0)
        else:
            aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('velero.openmetrics.health', ServiceCheck.OK)


@pytest.mark.e2e
def test_check_velero_e2e(dd_agent_check):
    assert_metrics(dd_agent_check(rate=True))


@pytest.mark.e2e
def test_check_velero_discovery_e2e(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=2)
    assert_metrics(aggregator)
