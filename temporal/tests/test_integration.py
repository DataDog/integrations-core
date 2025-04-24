# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.temporal import TemporalCheck

from .common import TAGS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_check(dd_run_check, aggregator, check):
    dd_run_check(check)

    for metric in get_metadata_metrics():
        aggregator.assert_metric(name=metric, at_least=0, tags=TAGS)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_service_checks(dd_run_check, aggregator, check):
    dd_run_check(check)
    aggregator.assert_service_check('temporal.server.openmetrics.health', TemporalCheck.OK, tags=TAGS)


def test_metadata(dd_run_check, datadog_agent, check):
    dd_run_check(check)

    expected_version_metadata = {
        'version.scheme': 'semver',
        'version.major': '1',
        'version.minor': '27',
        'version.patch': '2',
        'version.raw': '1.27.2',
    }

    datadog_agent.assert_metadata(check.check_id, expected_version_metadata)
