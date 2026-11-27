# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientInvalidURLError,
    HTTPClientReadTimeoutError,
    HTTPClientSSLError,
)
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


def test_auth():
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    assert hdfs_namenode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


@pytest.mark.parametrize(
    'outcome, message_prefix',
    [
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Request timeout', id='read timeout'),
        pytest.param(HTTPClientConnectTimeoutError('connect timed out'), 'Request timeout', id='connect timeout'),
        pytest.param(HTTPClientConnectionError('connection refused'), 'Request failed', id='connection error'),
        pytest.param(HTTPClientSSLError('certificate verify failed'), 'Request failed', id='ssl error'),
        pytest.param(HTTPClientInvalidURLError('invalid url'), 'Request failed', id='invalid url'),
        pytest.param(FakeHTTPResponse(status_code=500), 'Request failed', id='error status'),
        pytest.param(
            FakeHTTPResponse(json_error=json.JSONDecodeError('Expecting value', '', 0)),
            'JSON Parse failed',
            id='invalid json',
        ),
    ],
)
def test_request_failure_reports_critical(aggregator, fake_http, outcome, message_prefix):
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])
    fake_http.register_response('GET', NAME_SYSTEM_STATE_URL, outcome)

    with pytest.raises(Exception) as excinfo:
        hdfs_namenode.check(instance)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK,
        status=HDFSNameNode.CRITICAL,
        tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS,
        # The stub matches messages as regular expressions, and the URL contains `?`.
        message=re.escape('{}: {}, {}'.format(message_prefix, NAME_SYSTEM_STATE_URL, excinfo.value)),
        count=1,
    )
