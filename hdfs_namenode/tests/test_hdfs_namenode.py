# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re

import mock
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientInvalidURLError,
    HTTPClientReadTimeoutError,
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


def test_auth(aggregator, dd_run_check, mocked_request):
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    dd_run_check(hdfs_namenode)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
    )


def test_auth_configures_client():
    # Without the fake_http fixture, this is the client the check sends every request with
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    assert hdfs_namenode.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


@pytest.mark.parametrize(
    'outcome, expected_message',
    [
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Request timeout: {url}, read timed out', id='timeout'),
        pytest.param(
            HTTPClientConnectionError('connection refused'),
            'Request failed: {url}, connection refused',
            id='connection-error',
        ),
        pytest.param(HTTPClientInvalidURLError('invalid url'), 'Request failed: {url}, invalid url', id='invalid-url'),
        pytest.param({'status_code': 500}, 'Request failed: {url}, 500 Server Error', id='error-status'),
        pytest.param(
            {'content': b'not json', 'json_error': json.JSONDecodeError('Expecting value', 'not json', 0)},
            'JSON Parse failed: {url}, Expecting value: line 1 column 1 (char 0)',
            id='invalid-json',
        ),
    ],
)
def test_request_failure_reports_critical(
    aggregator, dd_run_check, fake_http, fake_http_response, outcome, expected_message
):
    if isinstance(outcome, Exception):
        fake_http.register_response('GET', NAME_SYSTEM_STATE_URL, outcome)
    else:
        fake_http_response(NAME_SYSTEM_STATE_URL, **outcome)
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    with pytest.raises(Exception):
        dd_run_check(hdfs_namenode)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK,
        HDFSNameNode.CRITICAL,
        tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS,
        message=re.escape(expected_message.format(url=NAME_SYSTEM_STATE_URL)),
        count=1,
    )
    fake_http.assert_all_responses_consumed()
