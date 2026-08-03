# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import (
    CUSTOM_TAGS,
    DATANODE_URI,
    HDFS_DATANODE_AUTH_CONFIG,
    HDFS_DATANODE_CONFIG,
    HDFS_DATANODE_METRIC_TAGS,
    HDFS_DATANODE_METRICS_VALUES,
    HDFS_RAW_VERSION,
    TEST_PASSWORD,
    TEST_USERNAME,
)

pytestmark = pytest.mark.unit

CHECK_ID = 'test:123'


def test_check(aggregator, mocked_request):
    """
    Test that we get all the metrics we're supposed to get
    Note: We don't do aggregator.assert_all_metrics_covered() because depending on timing, some other metrics may appear
    """

    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    # Run the check once
    hdfs_datanode.check(instance)

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    for metric, value in HDFS_DATANODE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1)


def test_metadata(aggregator, mocked_request, mocked_metadata_request, datadog_agent):
    """
    Test that we get the metadata we are expecting
    """

    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    # Run the check once
    hdfs_datanode.check_id = CHECK_ID
    hdfs_datanode.check(instance)

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    major, minor, patch = HDFS_RAW_VERSION.split('.')

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


def test_json_parse_failure_keeps_url_in_service_check(aggregator, mock_http):
    """The URL is the only per-bean discriminator, so a non-JSON body must still name it."""
    mock_http.get.side_effect = lambda url, *args, **kwargs: MockHTTPResponse(content='<html>not json</html>')
    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    with pytest.raises(ValueError):
        hdfs_datanode.check(instance)

    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)
    message = aggregator.service_checks(HDFSDataNode.JMX_SERVICE_CHECK)[0].message
    assert message.startswith('JSON Parse failed: {}'.format(DATANODE_URI))


def test_auth():
    instance = HDFS_DATANODE_AUTH_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    assert hdfs_datanode.http.get_basic_auth() == (TEST_USERNAME, TEST_PASSWORD)
