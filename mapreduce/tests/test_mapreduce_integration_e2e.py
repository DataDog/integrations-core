# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_integration_metrics(aggregator, check, instance, datadog_agent):
    check = check(instance)
    check.check(instance)

    for metric in common.ELAPSED_TIME_METRICS:
        aggregator.assert_metric(metric)
    assert_metrics_covered(aggregator)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, check, instance, datadog_agent):
    check = check(instance)
    check.check_id = 'test:123'
    check.check(instance)

    version_metadata = {
        'version.raw': '2.7.1',
        'version.scheme': 'semver',
        'version.major': '2',
        'version.minor': '7',
        'version.patch': '1',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in common.ELAPSED_TIME_BUCKET_METRICS:
        aggregator.assert_metric(metric)
    assert_metrics_covered(aggregator)


def assert_metrics_covered(aggregator):
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
