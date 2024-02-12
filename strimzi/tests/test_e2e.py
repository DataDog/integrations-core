# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck
from tests.common import (
    E2E_CLUSTER_OPERATOR_METRICS,
    FLAKY_E2E_METRICS,
    TOPIC_OPERATOR_METRICS,
    USER_OPERATOR_METRICS,
)

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for endpoint_metrics in (
        E2E_CLUSTER_OPERATOR_METRICS,
        TOPIC_OPERATOR_METRICS,
        USER_OPERATOR_METRICS,
    ):
        for expected_metric in endpoint_metrics:
            if expected_metric in FLAKY_E2E_METRICS:
                aggregator.assert_metric(expected_metric, at_least=0)
            else:
                aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for namespace in ("cluster_operator", "topic_operator", "user_operator"):
        aggregator.assert_service_check(
            f"strimzi.{namespace}.openmetrics.health",
            status=StrimziCheck.OK,
            count=2,  # because rate=True
        )
    assert len(aggregator.service_check_names) == 3
