# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = pytest.mark.integration

CHECK_ID = 'test:123'


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, dd_run_check, instance):
    check = check(instance)
    dd_run_check(check)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    for metric in common.OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, check, dd_run_check, instance, datadog_agent):
    check_instance = check(instance)
    check_instance.check_id = CHECK_ID
    dd_run_check(check_instance)

    major, minor, patch = common.HDFS_RAW_VERSION.split('.')

    version_metadata = {
        'version.raw': mock.ANY,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.build': mock.ANY,
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)
    datadog_agent.assert_metadata_count(6)
