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
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import (
    CUSTOM_TAGS,
    DATANODE_INFO_URL,
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


def test_auth():
    """
    Test that the configured credentials are sent with every request
    """
    instance = HDFS_DATANODE_AUTH_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    assert hdfs_datanode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


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
    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])
    fake_http.register_response('GET', DATANODE_INFO_URL, outcome)

    with pytest.raises(Exception) as excinfo:
        hdfs_datanode.check(instance)

    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK,
        status=HDFSDataNode.CRITICAL,
        tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS,
        # The stub matches messages as regular expressions, and the URL contains `?`.
        message=re.escape('{}: {}, {}'.format(message_prefix, DATANODE_INFO_URL, excinfo.value)),
        count=1,
    )
