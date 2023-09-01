# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.impala import ImpalaCheck

from .common import METRICS, TAGS


@pytest.mark.unit
@pytest.mark.metrics_file("catalog", "metrics.txt")
def test_catalog_mock_assert_metrics_using_metadata(dd_run_check, aggregator, catalog_check, mock_metrics):
    dd_run_check(catalog_check)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
@pytest.mark.metrics_file("catalog", "metrics.txt")
def test_catalog_mock_assert_service_check(dd_run_check, aggregator, catalog_check, mock_metrics):
    dd_run_check(catalog_check)
    aggregator.assert_service_check(
        "impala.catalog.openmetrics.health",
        status=ImpalaCheck.OK,
        tags=TAGS,
    )


@pytest.mark.unit
@pytest.mark.metrics_file("catalog", "metrics.txt")
def test_catalog_mock_assert_metrics(dd_run_check, aggregator, catalog_check, mock_metrics):
    dd_run_check(catalog_check)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            value=float(expected_metric["value"]) if "value" in expected_metric else None,
            metric_type=expected_metric.get("type", aggregator.GAUGE),
            tags=expected_metric.get("tags", TAGS),
            count=expected_metric.get("count", 1),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()
