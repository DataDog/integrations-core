# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.impala import ImpalaCheck

from .common import METRICS, TAGS


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_catalog_check_integration_assert_metrics(dd_run_check, aggregator, catalog_check):
    dd_run_check(catalog_check)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            metric_type=expected_metric.get("type", aggregator.GAUGE),
            tags=expected_metric.get("tags", TAGS),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_catalog_check_integration_assert_service_check(dd_run_check, aggregator, catalog_check):
    dd_run_check(catalog_check)
    aggregator.assert_service_check(
        "impala.catalog.openmetrics.health",
        status=ImpalaCheck.OK,
        tags=TAGS,
    )


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_catalog_check_integration_assert_metrics_using_metadata(dd_run_check, aggregator, catalog_check):
    dd_run_check(catalog_check)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
