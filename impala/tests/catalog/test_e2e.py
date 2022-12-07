# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.impala import ImpalaCheck

from ..common import get_e2e_metric_type
from .common import METRICS, TAGS


@pytest.mark.e2e
def test_catalog_check_e2e_assert_metrics(dd_agent_check, catalog_instance):
    aggregator = dd_agent_check(catalog_instance, rate=True)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=expected_metric["name"],
            metric_type=get_e2e_metric_type(expected_metric.get("type", aggregator.GAUGE)),
            tags=expected_metric.get("tags", TAGS),
        )

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_catalog_check_e2e_assert_service_check(dd_agent_check, catalog_instance):
    aggregator = dd_agent_check(catalog_instance, rate=True)
    aggregator.assert_service_check(
        "impala.catalog.openmetrics.health",
        status=ImpalaCheck.OK,
        tags=TAGS,
    )


@pytest.mark.e2e
def test_catalog_check_e2e_assert_metrics_using_metadata(dd_agent_check, catalog_instance):
    aggregator = dd_agent_check(catalog_instance, rate=True)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
