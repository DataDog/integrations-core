# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck

from .common import HERE, METRICS, STRIMZI_VERSION

pytestmark = pytest.mark.unit


def test_check(dd_run_check, aggregator, check, instance, tags, mock_http_response):
    mock_http_response(file_path=os.path.join(HERE, 'fixtures', STRIMZI_VERSION, 'metrics.txt'))
    dd_run_check(check(instance))

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            value=float(expected_metric["value"]) if "value" in expected_metric else None,
            tags=expected_metric.get("tags", tags),
            count=expected_metric.get("count", 1),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        "strimzi.openmetrics.health",
        status=StrimziCheck.OK,
        tags=tags,
        count=1,
    )
