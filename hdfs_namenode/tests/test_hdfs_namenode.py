# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPRequestError
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


def test_malformed_header_still_reports_critical(aggregator, dd_run_check, mock_http):
    """A server-sent malformed header must still emit hdfs.namenode.jmx.can_connect.

    A multi-valued Content-Length makes the backend reject the response header. The translator has
    no more specific agnostic subtype for that, so it arrives as a bare HTTPRequestError and the
    last arm has to name that type.
    """
    message = 'Content-Length contained multiple unmatching values'
    mock_http.get.side_effect = HTTPRequestError(message)
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    with pytest.raises(Exception, match=message):
        dd_run_check(hdfs_namenode)

    aggregator.assert_service_check(HDFSNameNode.JMX_SERVICE_CHECK, status=HDFSNameNode.CRITICAL, count=1)
    # The last arm reports the bare error text, unlike the status/connection arm above it, which
    # prefixes "Request failed". Pin the exact message so the arm cannot drift.
    assert aggregator.service_checks(HDFSNameNode.JMX_SERVICE_CHECK)[0].message == message


def test_auth():
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    assert hdfs_namenode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)
