# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import (
    CUSTOM_TAGS,
    HDFS_NAMENODE_AUTH_CONFIG,
    HDFS_NAMENODE_CONFIG,
    HDFS_NAMESYSTEM_METRIC_TAGS,
    HDFS_NAMESYSTEM_METRICS_VALUES,
    HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES,
    HDFS_NAMESYSTEM_STATE_METRICS_VALUES,
    HDFS_RAW_VERSION,
    NAMENODE_URI,
    TEST_PASSWORD,
    TEST_USERNAME,
)

pytestmark = pytest.mark.unit

CHECK_ID = 'test:123'


def test_check(aggregator, dd_run_check, mocked_request):
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    dd_run_check(hdfs_namenode)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    for metric, value in HDFS_NAMESYSTEM_STATE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1)

    for metric, value in HDFS_NAMESYSTEM_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1)

    for metric, value in HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=2)

    aggregator.assert_all_metrics_covered()


def test_metadata(aggregator, dd_run_check, mocked_request, datadog_agent):
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    hdfs_namenode.check_id = CHECK_ID
    dd_run_check(hdfs_namenode)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
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


def test_json_parse_failure_keeps_url_in_service_check(aggregator, dd_run_check, mock_http):
    """The URL is the only per-bean discriminator, so a non-JSON body must still name it."""
    mock_http.get.side_effect = lambda url, *args, **kwargs: MockHTTPResponse(content='<html>not json</html>')
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # `dd_run_check` re-raises the check's traceback as a plain Exception.
    with pytest.raises(Exception, match='JSONDecodeError'):
        dd_run_check(hdfs_namenode)

    message = aggregator.service_checks(HDFSNameNode.JMX_SERVICE_CHECK)[0].message
    assert message.startswith('JSON Parse failed: {}'.format(NAMENODE_URI))


def test_auth():
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    assert hdfs_namenode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)
