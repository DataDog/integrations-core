# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.temporal import TemporalCheck

from .common import METRICS, MOCKED_METRICS, TAGS

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=f"temporal.server.{expected_metric['name']}",
            value=expected_metric.get("value"),
            metric_type=expected_metric.get("type", aggregator.GAUGE),
            tags=expected_metric.get("tags", TAGS),
        )

    for metric in MOCKED_METRICS:
        aggregator.assert_metric(name=metric)
        for tag in TAGS:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()


def test_service_checks(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('temporal.server.openmetrics.health', TemporalCheck.OK, tags=TAGS)


def test_metadata(dd_run_check, datadog_agent, check, mock_metrics):
    dd_run_check(check)

    expected_version_metadata = {
        'version.scheme': 'semver',
        'version.major': '1',
        'version.minor': '27',
        'version.patch': '2',
        'version.raw': '1.27.2',
    }

    datadog_agent.assert_metadata(check.check_id, expected_version_metadata)
