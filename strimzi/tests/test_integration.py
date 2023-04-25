# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck
from tests.common import METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(dd_run_check, aggregator, check, instance, tags):
    dd_run_check(check(instance))

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            metric_type=expected_metric.get("type", aggregator.GAUGE),
            tags=expected_metric.get("tags", tags),
            count=expected_metric.get("count", 1),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_no_duplicate_all()
    aggregator.assert_service_check(
        "strimzi.openmetrics.health",
        status=StrimziCheck.OK,
        tags=tags,
        count=1,
    )
