# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from . import common

pytestmark = pytest.mark.integration

CHECK_ID = 'test:123'


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check = check(instance)
    check.check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, check, instance, datadog_agent):
    check = check(instance)
    check.check_id = CHECK_ID
    check.check(instance)

    major, minor, patch = common.HDFS_RAW_VERSION.split('.')

    version_metadata = {
        'version.raw': common.HDFS_RAW_VERSION,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)
    datadog_agent.assert_metadata_count(5)
