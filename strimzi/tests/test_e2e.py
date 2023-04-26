# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck
from tests.common import CLUSTER_OPERATOR_METRICS, TOPIC_OPERATOR_METRICS, USER_OPERATOR_METRICS

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for endpoint_metrics in (CLUSTER_OPERATOR_METRICS, TOPIC_OPERATOR_METRICS, USER_OPERATOR_METRICS):
        for expected_metric in endpoint_metrics:
            aggregator.assert_metric(
                name=expected_metric["name"],
                count=expected_metric.get("count", 1),
            )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for namespace in ('cluster_operator', 'topic_operator', 'user_operator'):
        aggregator.assert_service_check(
            f"strimzi.{namespace}.openmetrics.health",
            status=StrimziCheck.OK,
            count=2,  # because rate=True
        )
