# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_integration_metrics(aggregator, check, dd_run_check, instance, datadog_agent):
    check = check(instance)
    with common.mock_local_mapreduce_dns():
        dd_run_check(check)

    for metric in common.ELAPSED_TIME_METRICS:
        aggregator.assert_metric(metric)
    assert_metrics_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, check, dd_run_check, instance, datadog_agent):
    check = check(instance)
    check.check_id = 'test:123'
    with common.mock_local_mapreduce_dns():
        dd_run_check(check)

    version_metadata = {
        'version.raw': '3.2.1',
        'version.scheme': 'semver',
        'version.major': '3',
        'version.minor': '2',
        'version.patch': '1',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    # trigger a job but wait for it to be in a running state before running check
    assert common.setup_mapreduce()

    aggregator = dd_agent_check(instance, rate=True)
    for metric in common.ELAPSED_TIME_BUCKET_METRICS:
        aggregator.assert_metric(metric)
    assert_metrics_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def assert_metrics_covered(aggregator):
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
