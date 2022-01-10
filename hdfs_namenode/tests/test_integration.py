# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from . import common

pytestmark = pytest.mark.integration

CHECK_ID = 'test:123'


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, dd_run_check, check, instance):
    check = check(instance)
    dd_run_check(check)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, dd_run_check, check, instance, datadog_agent):
    check = check(instance)
    check.check_id = CHECK_ID
    dd_run_check(check)

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
