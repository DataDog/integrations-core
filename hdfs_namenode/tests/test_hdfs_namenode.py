# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from json import JSONDecodeError

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientRequestError
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
    NAME_SYSTEM_STATE_URL,
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


def test_json_parse_failure_keeps_url_in_service_check(aggregator, fake_http):
    fake_http.register_response(
        'GET',
        NAME_SYSTEM_STATE_URL,
        FakeHTTPResponse(json_error=JSONDecodeError('invalid JSON', '<html>not json</html>', 0)),
    )
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    with pytest.raises(JSONDecodeError):
        hdfs_namenode.check(instance)

    aggregator.assert_service_check(HDFSNameNode.JMX_SERVICE_CHECK, status=HDFSNameNode.CRITICAL, count=1)
    assert aggregator.service_checks(HDFSNameNode.JMX_SERVICE_CHECK)[0].message.startswith(
        f'JSON Parse failed: {NAMENODE_URI}'
    )


def test_malformed_header_still_reports_critical(aggregator, fake_http):
    message = 'Content-Length contained multiple unmatching values'
    fake_http.register_response('GET', NAME_SYSTEM_STATE_URL, HTTPClientRequestError(message))
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    with pytest.raises(HTTPClientRequestError, match=message):
        hdfs_namenode.check(instance)

    aggregator.assert_service_check(HDFSNameNode.JMX_SERVICE_CHECK, status=HDFSNameNode.CRITICAL, count=1)
    assert aggregator.service_checks(HDFSNameNode.JMX_SERVICE_CHECK)[0].message == message


def test_auth():
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    assert hdfs_namenode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)
