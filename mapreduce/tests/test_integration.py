# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import ELAPSED_TIME_METRICS, assert_metrics_covered, mock_local_mapreduce_dns

pytestmark = [pytest.mark.usefixtures('dd_environment')]


def test_integration_metrics(aggregator, check, dd_run_check, instance, datadog_agent):
    check = check(instance)
    with mock_local_mapreduce_dns():
        dd_run_check(check)

    for metric in ELAPSED_TIME_METRICS:
        aggregator.assert_metric(metric)

    assert_metrics_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_metadata(aggregator, check, dd_run_check, instance, datadog_agent):
    check = check(instance)
    check.check_id = 'test:123'
    with mock_local_mapreduce_dns():
        dd_run_check(check)

    version_metadata = {
        'version.raw': '3.2.1',
        'version.scheme': 'semver',
        'version.major': '3',
        'version.minor': '2',
        'version.patch': '1',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)
