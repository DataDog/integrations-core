# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck
from tests.common import METRICS

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, instance, tags):
    aggregator = dd_agent_check(instance, rate=True)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            tags=expected_metric.get("tags", tags),
            count=expected_metric.get("count", 1),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        "strimzi.openmetrics.health",
        status=StrimziCheck.OK,
        tags=tags,
        count=2,  # because rate=True
    )
