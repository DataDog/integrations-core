# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
import ssl
import threading
import time
from http import server as BaseHTTPServer
from typing import Any
from urllib.parse import urljoin

import mock
import pytest
import urllib3

from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
    HTTPClientRequestError,
    HTTPClientStatusError,
)
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.spark import SparkCheck

from .common import CLUSTER_NAME, CLUSTER_TAGS, INSTANCE_DRIVER_1, INSTANCE_DRIVER_2, INSTANCE_STANDALONE

# IDs
YARN_APP_ID = 'application_1459362484344_0011'
SPARK_APP_ID = 'app_001'
SPARK_APP2_ID = 'app_002'

APP_NAME = 'PySparkShell'

# URLs for cluster managers
SPARK_APP_URL = 'http://localhost:4040'
SPARK_YARN_URL = 'http://localhost:8088'
SPARK_MESOS_URL = 'http://localhost:5050'
STANDALONE_URL = 'http://localhost:8080'

# SSL test server
SSL_SERVER_PORT = 44443
SSL_SERVER_ADDRESS = 'localhost'
SSL_SERVER_URL = 'https://{}:{}'.format(SSL_SERVER_ADDRESS, SSL_SERVER_PORT)

# URL Paths
SPARK_REST_PATH = 'api/v1/applications'
YARN_APPS_PATH = 'ws/v1/cluster/apps'
MESOS_APPS_PATH = 'frameworks'
STANDALONE_APPS_PATH = 'json/'
STANDALONE_APP_PATH_HTML = 'app/'
VERSION_PATH = '/api/v1/version'

# Service Check Names
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
MESOS_SERVICE_CHECK = 'spark.mesos_master.can_connect'
SPARK_DRIVER_SERVICE_CHECK = 'spark.driver.can_connect'
STANDALONE_SERVICE_CHECK = 'spark.standalone_master.can_connect'

TEST_USERNAME = 'admin'
TEST_PASSWORD = 'password'

CUSTOM_TAGS = ['optional:tag1']
COMMON_TAGS = [
    'app_name:' + APP_NAME,
] + CLUSTER_TAGS


def join_url_dir(url, *args):
    """
    Join a URL with multiple directories
    """
    for path in args:
        url = url.rstrip('/') + '/'
        url = urljoin(url, path.lstrip('/'))

    return url


# Spark Version URL
SPARK_VERSION_URL = urljoin(SPARK_APP_URL, VERSION_PATH)

# YARN Service URLs
YARN_APP_BASE_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID)
YARN_APP_URL = urljoin(SPARK_YARN_URL, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=SPARK'
YARN_SPARK_VERSION_URL = join_url_dir(YARN_APP_BASE_URL, VERSION_PATH)
YARN_SPARK_APP_URL = join_url_dir(YARN_APP_BASE_URL, SPARK_REST_PATH)
YARN_SPARK_JOB_URL = join_url_dir(YARN_APP_BASE_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')
YARN_SPARK_STAGE_URL = join_url_dir(YARN_APP_BASE_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages')
YARN_SPARK_EXECUTOR_URL = join_url_dir(YARN_APP_BASE_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
YARN_SPARK_RDD_URL = join_url_dir(YARN_APP_BASE_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')
YARN_SPARK_STREAMING_STATISTICS_URL = join_url_dir(
    YARN_APP_BASE_URL, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics'
)
YARN_SPARK_METRICS_JSON_URL = join_url_dir(YARN_APP_BASE_URL, 'metrics/json')

# Mesos Service URLs
MESOS_APP_URL = urljoin(SPARK_MESOS_URL, MESOS_APPS_PATH)

# Driver Service URLs
DRIVER_APP_URL = urljoin(SPARK_APP_URL, SPARK_REST_PATH)

# Spark Standalone Service URLs
STANDALONE_APP_URL = urljoin(STANDALONE_URL, STANDALONE_APPS_PATH)
STANDALONE_APP_HTML_URL = urljoin(STANDALONE_URL, STANDALONE_APP_PATH_HTML) + '?appId=' + SPARK_APP_ID

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')


def _json_response(json_result: Any) -> FakeHTTPResponse:
    text = json.dumps(json_result)
    return FakeHTTPResponse(content=text.encode('utf-8'), text=text, json_result=json_result)


def _json_response_from_fixture(filename: str) -> FakeHTTPResponse:
    with open(os.path.join(FIXTURE_DIR, filename), encoding='utf-8') as response_file:
        text = response_file.read()
    return FakeHTTPResponse(content=text.encode('utf-8'), text=text, json_result=json.loads(text))


def _text_response_from_fixture(filename: str) -> FakeHTTPResponse:
    with open(os.path.join(FIXTURE_DIR, filename), encoding='utf-8') as response_file:
        text = response_file.read()
    return FakeHTTPResponse(content=text.encode('utf-8'), text=text)


def _invalid_json_response(text: str) -> FakeHTTPResponse:
    return FakeHTTPResponse(
        content=text.encode('utf-8'),
        text=text,
        json_error=json.JSONDecodeError('Expecting value', text, 0),
    )


def _status_response(status_code: int) -> FakeHTTPResponse:
    error_kind = 'Client Error' if status_code < 500 else 'Server Error'
    return FakeHTTPResponse(
        status_code=status_code,
        status_error=HTTPClientStatusError(f'{status_code} {error_kind}'),
    )


APPLICATION_RESPONSE_FIXTURES = {
    'jobs': 'job_metrics',
    'stages': 'stage_metrics',
    'executors': 'executor_metrics',
    'storage/rdd': 'rdd_metrics',
    'streaming/statistics': 'streaming_statistics',
}


def _register_response(
    fake_http: FakeHTTPClient,
    url: str,
    response: FakeHTTPResponse | Exception,
    *,
    cookies: dict[str, str] | None = None,
) -> None:
    fake_http.register_response('GET', url, response, match_options={'cookies': cookies})
    expected_requests = getattr(fake_http, '_spark_expected_requests', None)
    if expected_requests is None:
        expected_requests = []
        fake_http._spark_expected_requests = expected_requests
    expected_requests.append(RecordedRequest('GET', url, {'cookies': cookies}))


def _assert_http_requests(fake_http: FakeHTTPClient) -> None:
    expected_requests = getattr(fake_http, '_spark_expected_requests', [])
    verified_count = getattr(fake_http, '_spark_verified_request_count', 0)
    actual_requests = fake_http.requests[verified_count:]
    remaining_requests = list(expected_requests)
    unexpected_requests = []
    for request in actual_requests:
        if request in remaining_requests:
            remaining_requests.remove(request)
        else:
            unexpected_requests.append(request)
    assert not unexpected_requests, f'Unexpected Spark HTTP requests: {unexpected_requests!r}'
    assert not remaining_requests, f'Expected Spark HTTP requests were not made: {remaining_requests!r}'
    fake_http.assert_all_responses_consumed()
    expected_requests.clear()
    fake_http._spark_verified_request_count = len(fake_http.requests)


def _register_fixture_response(fake_http: FakeHTTPClient, url: str, filename: str) -> None:
    _register_response(fake_http, url, _json_response_from_fixture(filename))


def _register_text_fixture_response(
    fake_http: FakeHTTPClient,
    url: str,
    filename: str,
    *,
    cookies: dict[str, str] | None = None,
) -> None:
    _register_response(fake_http, url, _text_response_from_fixture(filename), cookies=cookies)


def _proxy_approved_url(url: str) -> str:
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}proxyapproved=true'


def _register_application_responses(
    fake_http: FakeHTTPClient,
    base_url: str,
    app_id: str = SPARK_APP_ID,
    *,
    include_stages: bool = True,
    proxy_approved: bool = False,
    overrides: dict[str, FakeHTTPResponse] | None = None,
) -> None:
    overrides = overrides or {}
    for path, fixture_name in APPLICATION_RESPONSE_FIXTURES.items():
        if path == 'stages' and not include_stages:
            continue
        url = join_url_dir(base_url, SPARK_REST_PATH, app_id, path)
        if proxy_approved:
            url = _proxy_approved_url(url)
        response = overrides[url] if url in overrides else _json_response_from_fixture(fixture_name)
        _register_response(fake_http, url, response, cookies={'proxy_cookie': 'foo'} if proxy_approved else None)

    metrics_url = join_url_dir(base_url, 'metrics/json')
    if proxy_approved:
        metrics_url = _proxy_approved_url(metrics_url)
    _register_response(
        fake_http,
        metrics_url,
        _json_response_from_fixture('metrics_json'),
        cookies={'proxy_cookie': 'foo'} if proxy_approved else None,
    )


def _register_yarn_responses(fake_http: FakeHTTPClient) -> None:
    _register_fixture_response(fake_http, YARN_APP_URL, 'yarn_apps')
    _register_fixture_response(fake_http, YARN_SPARK_VERSION_URL, 'version')
    _register_fixture_response(fake_http, YARN_SPARK_APP_URL, 'spark_apps')
    _register_application_responses(fake_http, YARN_APP_BASE_URL)


def _register_mesos_responses(fake_http: FakeHTTPClient) -> None:
    _register_fixture_response(fake_http, MESOS_APP_URL, 'mesos_apps')
    _register_fixture_response(fake_http, SPARK_VERSION_URL, 'version')
    _register_fixture_response(fake_http, DRIVER_APP_URL, 'spark_apps')
    _register_application_responses(fake_http, SPARK_APP_URL)


def _register_driver_responses(fake_http: FakeHTTPClient) -> None:
    _register_fixture_response(fake_http, SPARK_VERSION_URL, 'version')
    _register_fixture_response(fake_http, DRIVER_APP_URL, 'spark_apps')
    _register_application_responses(fake_http, SPARK_APP_URL)


def _register_standalone_pre20_responses(fake_http: FakeHTTPClient) -> None:
    _register_standalone_responses(fake_http, pre_20=True)


def _register_standalone_responses(
    fake_http: FakeHTTPClient,
    *,
    include_stages: bool = True,
    pre_20: bool = False,
    proxy_warning: bool = False,
) -> None:
    if proxy_warning:
        redirect_url = _proxy_approved_url(STANDALONE_APP_URL)
        with open(os.path.join(FIXTURE_DIR, 'html_warning_page'), encoding='utf-8') as response_file:
            body = response_file.read().replace('$REDIRECT_URL$', redirect_url)
        _register_response(
            fake_http,
            STANDALONE_APP_URL,
            FakeHTTPResponse(content=body.encode('utf-8'), text=body, cookies={'proxy_cookie': 'foo'}),
        )
        _register_response(
            fake_http,
            redirect_url,
            _json_response_from_fixture('spark_standalone_apps'),
            cookies={'proxy_cookie': 'foo'},
        )
        _register_text_fixture_response(
            fake_http,
            _proxy_approved_url(STANDALONE_APP_HTML_URL),
            'spark_standalone_app',
            cookies={'proxy_cookie': 'foo'},
        )
        _register_response(
            fake_http,
            _proxy_approved_url(SPARK_VERSION_URL),
            _json_response_from_fixture('version'),
            cookies={'proxy_cookie': 'foo'},
        )
        _register_application_responses(
            fake_http,
            SPARK_APP_URL,
            include_stages=include_stages,
            proxy_approved=True,
        )
        return

    _register_fixture_response(fake_http, STANDALONE_APP_URL, 'spark_standalone_apps')
    _register_text_fixture_response(fake_http, STANDALONE_APP_HTML_URL, 'spark_standalone_app')
    _register_fixture_response(fake_http, SPARK_VERSION_URL, 'version')
    if pre_20:
        _register_fixture_response(fake_http, DRIVER_APP_URL, 'spark_apps_pre20')
    _register_application_responses(
        fake_http,
        SPARK_APP_URL,
        APP_NAME if pre_20 else SPARK_APP_ID,
        include_stages=include_stages,
    )


CHECK_NAME = 'spark'

YARN_CONFIG = {
    'spark_url': 'http://localhost:8088',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_yarn_mode',
    'executor_level_metrics': True,
    'tags': list(CUSTOM_TAGS),
}

YARN_AUTH_CONFIG = {
    'spark_url': 'http://localhost:8088',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_yarn_mode',
    'executor_level_metrics': True,
    'tags': list(CUSTOM_TAGS),
    'username': TEST_USERNAME,
    'password': TEST_PASSWORD,
}

MESOS_CONFIG = {
    'spark_url': 'http://localhost:5050',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_mesos_mode',
    'executor_level_metrics': True,
    'tags': list(CUSTOM_TAGS),
}

MESOS_FILTERED_CONFIG = {
    'spark_url': 'http://localhost:5050',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_mesos_mode',
    'executor_level_metrics': True,
    'spark_ui_ports': [1234],
}

DRIVER_CONFIG = {
    'spark_url': 'http://localhost:4040',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_driver_mode',
    'executor_level_metrics': True,
    'tags': list(CUSTOM_TAGS),
}

STANDALONE_CONFIG = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'executor_level_metrics': True,
}

STANDALONE_CONFIG_STAGE_DISABLED = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'executor_level_metrics': True,
    'disable_spark_stage_metrics': True,
    'disable_spark_job_stage_tags': True,
}

STANDALONE_CONFIG_PRE_20 = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'executor_level_metrics': True,
    'spark_pre_20_mode': 'true',
}

SSL_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'executor_level_metrics': True,
}

SSL_NO_VERIFY_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'executor_level_metrics': True,
    'ssl_verify': False,
}

SSL_CERT_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'ssl_verify': True,
    'ssl_ca_cert': os.path.join(CERTIFICATE_DIR, 'cert.cert'),
    'executor_level_metrics': True,
}

SPARK_JOB_RUNNING_METRIC_VALUES = {
    'spark.job.count': 2,
    'spark.job.num_tasks': 20,
    'spark.job.num_active_tasks': 30,
    'spark.job.num_completed_tasks': 40,
    'spark.job.num_skipped_tasks': 50,
    'spark.job.num_failed_tasks': 60,
    'spark.job.num_active_stages': 70,
    'spark.job.num_completed_stages': 80,
    'spark.job.num_skipped_stages': 90,
    'spark.job.num_failed_stages': 100,
}

SPARK_JOB_RUNNING_METRIC_TAGS = [
    'status:running',
    'job_id:0',
    'stage_id:0',
    'stage_id:1',
] + COMMON_TAGS

SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS = [
    'status:running',
    'job_id:0',
] + COMMON_TAGS

SPARK_JOB_SUCCEEDED_METRIC_VALUES = {
    'spark.job.count': 3,
    'spark.job.num_tasks': 1000,
    'spark.job.num_active_tasks': 2000,
    'spark.job.num_completed_tasks': 3000,
    'spark.job.num_skipped_tasks': 4000,
    'spark.job.num_failed_tasks': 5000,
    'spark.job.num_active_stages': 6000,
    'spark.job.num_completed_stages': 7000,
    'spark.job.num_skipped_stages': 8000,
    'spark.job.num_failed_stages': 9000,
}

SPARK_JOB_SUCCEEDED_METRIC_TAGS = [
    'status:succeeded',
    'job_id:0',
    'stage_id:0',
    'stage_id:1',
] + COMMON_TAGS

SPARK_JOB_SUCCEEDED_NO_STAGE_METRIC_TAGS = [
    'status:succeeded',
    'job_id:0',
] + COMMON_TAGS

SPARK_STAGE_RUNNING_METRIC_VALUES = {
    'spark.stage.count': 3,
    'spark.stage.num_active_tasks': 3 * 3,
    'spark.stage.num_complete_tasks': 4 * 3,
    'spark.stage.num_failed_tasks': 5 * 3,
    'spark.stage.executor_run_time': 6 * 3,
    'spark.stage.input_bytes': 7 * 3,
    'spark.stage.input_records': 8 * 3,
    'spark.stage.output_bytes': 9 * 3,
    'spark.stage.output_records': 10 * 3,
    'spark.stage.shuffle_read_bytes': 11 * 3,
    'spark.stage.shuffle_read_records': 12 * 3,
    'spark.stage.shuffle_write_bytes': 13 * 3,
    'spark.stage.shuffle_write_records': 14 * 3,
    'spark.stage.memory_bytes_spilled': 15 * 3,
    'spark.stage.disk_bytes_spilled': 16 * 3,
}

SPARK_STAGE_RUNNING_METRIC_TAGS = [
    'status:running',
    'stage_id:1',
] + COMMON_TAGS

SPARK_STAGE_COMPLETE_METRIC_VALUES = {
    'spark.stage.count': 2,
    'spark.stage.num_active_tasks': 100 * 2,
    'spark.stage.num_complete_tasks': 101 * 2,
    'spark.stage.num_failed_tasks': 102 * 2,
    'spark.stage.executor_run_time': 103 * 2,
    'spark.stage.input_bytes': 104 * 2,
    'spark.stage.input_records': 105 * 2,
    'spark.stage.output_bytes': 106 * 2,
    'spark.stage.output_records': 107 * 2,
    'spark.stage.shuffle_read_bytes': 108 * 2,
    'spark.stage.shuffle_read_records': 109 * 2,
    'spark.stage.shuffle_write_bytes': 110 * 2,
    'spark.stage.shuffle_write_records': 111 * 2,
    'spark.stage.memory_bytes_spilled': 112 * 2,
    'spark.stage.disk_bytes_spilled': 113 * 2,
}

SPARK_STAGE_COMPLETE_METRIC_TAGS = [
    'status:complete',
    'stage_id:0',
] + COMMON_TAGS

SPARK_DRIVER_METRIC_VALUES = {
    'spark.driver.rdd_blocks': 99,
    'spark.driver.memory_used': 98,
    'spark.driver.disk_used': 97,
    'spark.driver.active_tasks': 96,
    'spark.driver.failed_tasks': 95,
    'spark.driver.completed_tasks': 94,
    'spark.driver.total_tasks': 93,
    'spark.driver.total_duration': 92,
    'spark.driver.total_input_bytes': 91,
    'spark.driver.total_shuffle_read': 90,
    'spark.driver.total_shuffle_write': 89,
    'spark.driver.max_memory': 278019440,
    'spark.driver.mem.used_on_heap_storage': 79283,
    'spark.driver.mem.used_off_heap_storage': 0,
    'spark.driver.mem.total_on_heap_storage': 384093388,
    'spark.driver.mem.total_off_heap_storage': 0,
}

SPARK_DRIVER_OPTIONAL_METRIC_VALUES = {
    'spark.driver.peak_mem.jvm_heap_memory': 345498432,
    'spark.driver.peak_mem.jvm_off_heap_memory': 196924864,
    'spark.driver.peak_mem.on_heap_execution': 0,
    'spark.driver.peak_mem.off_heap_execution': 0,
    'spark.driver.peak_mem.on_heap_storage': 2445933,
    'spark.driver.peak_mem.off_heap_storage': 0,
    'spark.driver.peak_mem.on_heap_unified': 2445933,
    'spark.driver.peak_mem.off_heap_unified': 0,
    'spark.driver.peak_mem.direct_pool': 276762,
    'spark.driver.peak_mem.mapped_pool': 0,
    'spark.driver.peak_mem.minor_gc_count': 118,
    'spark.driver.peak_mem.minor_gc_time': 1436,
    'spark.driver.peak_mem.major_gc_count': 4,
    'spark.driver.peak_mem.major_gc_time': 419,
    'spark.driver.peak_mem.process_tree_jvm': 0,
    'spark.driver.peak_mem.process_tree_jvm_rss': 0,
    'spark.driver.peak_mem.process_tree_python': 0,
    'spark.driver.peak_mem.process_tree_python_rss': 0,
    'spark.driver.peak_mem.process_tree_other': 0,
    'spark.driver.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_METRIC_VALUES = {
    'spark.executor.count': 2,
    'spark.executor.rdd_blocks': 1,
    'spark.executor.memory_used': 2,
    'spark.executor.disk_used': 3,
    'spark.executor.active_tasks': 4,
    'spark.executor.failed_tasks': 5,
    'spark.executor.completed_tasks': 6,
    'spark.executor.total_tasks': 7,
    'spark.executor.total_duration': 8,
    'spark.executor.total_input_bytes': 9,
    'spark.executor.total_shuffle_read': 10,
    'spark.executor.total_shuffle_write': 11,
    'spark.executor.max_memory': 555755765,
    'spark.executor.mem.used_on_heap_storage': 79283,
    'spark.executor.mem.used_off_heap_storage': 0,
    'spark.executor.mem.total_on_heap_storage': 384093388,
    'spark.executor.mem.total_off_heap_storage': 0,
}

SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES = {
    'spark.executor.peak_mem.jvm_heap_memory': 361970928,
    'spark.executor.peak_mem.jvm_off_heap_memory': 94409256,
    'spark.executor.peak_mem.on_heap_execution': 16777216,
    'spark.executor.peak_mem.off_heap_execution': 0,
    'spark.executor.peak_mem.on_heap_storage': 2181737,
    'spark.executor.peak_mem.off_heap_storage': 0,
    'spark.executor.peak_mem.on_heap_unified': 18958953,
    'spark.executor.peak_mem.off_heap_unified': 0,
    'spark.executor.peak_mem.direct_pool': 8710,
    'spark.executor.peak_mem.mapped_pool': 0,
    'spark.executor.peak_mem.minor_gc_count': 988,
    'spark.executor.peak_mem.minor_gc_time': 5670,
    'spark.executor.peak_mem.major_gc_count': 3,
    'spark.executor.peak_mem.major_gc_time': 252,
    'spark.executor.peak_mem.process_tree_jvm': 0,
    'spark.executor.peak_mem.process_tree_jvm_rss': 0,
    'spark.executor.peak_mem.process_tree_python': 0,
    'spark.executor.peak_mem.process_tree_python_rss': 0,
    'spark.executor.peak_mem.process_tree_other': 0,
    'spark.executor.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_LEVEL_METRIC_VALUES = {
    'spark.executor.id.rdd_blocks': 1,
    'spark.executor.id.memory_used': 2,
    'spark.executor.id.disk_used': 3,
    'spark.executor.id.active_tasks': 4,
    'spark.executor.id.failed_tasks': 5,
    'spark.executor.id.completed_tasks': 6,
    'spark.executor.id.total_tasks': 7,
    'spark.executor.id.total_duration': 8,
    'spark.executor.id.total_input_bytes': 9,
    'spark.executor.id.total_shuffle_read': 10,
    'spark.executor.id.total_shuffle_write': 11,
    'spark.executor.id.max_memory': 555755765,
    'spark.executor.id.mem.used_on_heap_storage': 79283,
    'spark.executor.id.mem.used_off_heap_storage': 0,
    'spark.executor.id.mem.total_on_heap_storage': 384093388,
    'spark.executor.id.mem.total_off_heap_storage': 0,
}

SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES = {
    'spark.executor.id.peak_mem.jvm_heap_memory': 361970928,
    'spark.executor.id.peak_mem.jvm_off_heap_memory': 94409256,
    'spark.executor.id.peak_mem.on_heap_execution': 16777216,
    'spark.executor.id.peak_mem.off_heap_execution': 0,
    'spark.executor.id.peak_mem.on_heap_storage': 2181737,
    'spark.executor.id.peak_mem.off_heap_storage': 0,
    'spark.executor.id.peak_mem.on_heap_unified': 18958953,
    'spark.executor.id.peak_mem.off_heap_unified': 0,
    'spark.executor.id.peak_mem.direct_pool': 8710,
    'spark.executor.id.peak_mem.mapped_pool': 0,
    'spark.executor.id.peak_mem.minor_gc_count': 988,
    'spark.executor.id.peak_mem.minor_gc_time': 5670,
    'spark.executor.id.peak_mem.major_gc_count': 3,
    'spark.executor.id.peak_mem.major_gc_time': 252,
    'spark.executor.id.peak_mem.process_tree_jvm': 0,
    'spark.executor.id.peak_mem.process_tree_jvm_rss': 0,
    'spark.executor.id.peak_mem.process_tree_python': 0,
    'spark.executor.id.peak_mem.process_tree_python_rss': 0,
    'spark.executor.id.peak_mem.process_tree_other': 0,
    'spark.executor.id.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_LEVEL_METRIC_TAGS = [
    'executor_id:1',
] + COMMON_TAGS

SPARK_RDD_METRIC_VALUES = {
    'spark.rdd.count': 1,
    'spark.rdd.num_partitions': 2,
    'spark.rdd.num_cached_partitions': 2,
    'spark.rdd.memory_used': 284,
    'spark.rdd.disk_used': 0,
}

SPARK_STREAMING_STATISTICS_METRIC_VALUES = {
    'spark.streaming.statistics.avg_input_rate': 1.0,
    'spark.streaming.statistics.avg_processing_time': 175,
    'spark.streaming.statistics.avg_scheduling_delay': 8,
    'spark.streaming.statistics.avg_total_delay': 183,
    'spark.streaming.statistics.batch_duration': 2000,
    'spark.streaming.statistics.num_active_batches': 2,
    'spark.streaming.statistics.num_active_receivers': 1,
    'spark.streaming.statistics.num_inactive_receivers': 3,
    'spark.streaming.statistics.num_processed_records': 7,
    'spark.streaming.statistics.num_received_records': 9,
    'spark.streaming.statistics.num_receivers': 10,
    'spark.streaming.statistics.num_retained_completed_batches': 27,
    'spark.streaming.statistics.num_total_completed_batches': 28,
}

SPARK_STRUCTURED_STREAMING_METRIC_VALUES = {
    'spark.structured_streaming.input_rate': 12,
    'spark.structured_streaming.latency': 12,
    'spark.structured_streaming.processing_rate': 12,
    'spark.structured_streaming.rows_count': 12,
    'spark.structured_streaming.used_bytes': 12,
}

SPARK_STRUCTURED_STREAMING_METRIC_NO_TAGS = {
    'spark.structured_streaming.input_rate',
    'spark.structured_streaming.latency',
}

SPARK_STRUCTURED_STREAMING_METRIC_PUNCTUATED_TAGS = {
    # Metric to test for punctuation in the query names of stream metrics.
    'spark.structured_streaming.input_rate': 100,
    'spark.structured_streaming.latency': 100,
    'spark.structured_streaming.processing_rate': 100,
}


def _assert(aggregator, values_and_tags):
    for m_vals, tags in values_and_tags:
        for metric, value in m_vals.items():
            aggregator.assert_metric(metric, value=value, tags=tags)


@pytest.mark.unit
def test_yarn(aggregator, dd_run_check, fake_http):
    _register_yarn_responses(fake_http)
    c = SparkCheck('spark', {}, [YARN_CONFIG])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS),
            # Check the optional executor level metrics
            (
                SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS,
            ),
            # Check the summary executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
        ],
    )
    tags = ['url:http://localhost:8088'] + CLUSTER_TAGS + CUSTOM_TAGS
    tags.sort()

    for sc in aggregator.service_checks(YARN_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        sc.tags.sort()
        assert sc.tags == tags
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        sc.tags.sort()
        assert sc.tags == tags

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_auth_yarn_config():
    c = SparkCheck('spark', {}, [YARN_AUTH_CONFIG])
    assert c.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


@pytest.mark.unit
def test_auth_yarn(aggregator, dd_run_check, fake_http):
    _register_yarn_responses(fake_http)
    c = SparkCheck('spark', {}, [YARN_AUTH_CONFIG])
    dd_run_check(c)
    for sc in aggregator.service_checks(YARN_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_mesos(aggregator, dd_run_check, fake_http):
    _register_mesos_responses(fake_http)
    c = SparkCheck('spark', {}, [MESOS_CONFIG])
    dd_run_check(c)
    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS),
            # Check the optional executor level metrics
            (
                SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS,
            ),
            # Check the summary executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the streaming statistics metrics,
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
        ],
    )
    # Check the service tests

    for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        tags = ['url:http://localhost:5050'] + CLUSTER_TAGS + CUSTOM_TAGS
        tags.sort()
        sc.tags.sort()
        assert sc.tags == tags
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        tags = ['url:http://localhost:4040'] + CLUSTER_TAGS + CUSTOM_TAGS
        tags.sort()
        sc.tags.sort()
        assert sc.tags == tags

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_mesos_filter(aggregator, dd_run_check, fake_http):
    _register_fixture_response(fake_http, MESOS_APP_URL, 'mesos_apps')
    c = SparkCheck('spark', {}, [MESOS_FILTERED_CONFIG])
    dd_run_check(c)

    for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:5050'] + CLUSTER_TAGS

    assert aggregator.metrics_asserted_pct == 100.0
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_driver_unit(aggregator, dd_run_check, fake_http):
    _register_driver_responses(fake_http)
    c = SparkCheck('spark', {}, [DRIVER_CONFIG])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS),
            # Check the optional executor level metrics
            (
                SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS,
            ),
            # Check the summary executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS),
        ],
    )
    # Check the service tests

    for sc in aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        tags = ['url:http://localhost:4040'] + CLUSTER_TAGS + CUSTOM_TAGS
        tags.sort()
        sc.tags.sort()
        assert sc.tags == tags
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        tags = ['url:http://localhost:4040'] + CLUSTER_TAGS + CUSTOM_TAGS
        tags.sort()
        sc.tags.sort()
        assert sc.tags == tags

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_standalone_unit(aggregator, dd_run_check, fake_http):
    _register_standalone_responses(fake_http)
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the optional executor level metrics
            (SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS),
        ],
    )
    # Check the service tests
    for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:8080'] + CLUSTER_TAGS
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:4040'] + CLUSTER_TAGS

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_standalone_stage_disabled_unit(aggregator, dd_run_check, fake_http):
    _register_standalone_responses(fake_http, include_stages=False)
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG_STAGE_DISABLED])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS),
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_NO_STAGE_METRIC_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the optional executor level metrics
            (SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS),
        ],
    )
    # Check the service tests
    for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:8080'] + CLUSTER_TAGS
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:4040'] + CLUSTER_TAGS

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_standalone_unit_with_proxy_warning_page(aggregator, dd_run_check, fake_http):
    _register_standalone_responses(fake_http, proxy_warning=True)
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the optional executor level metrics
            (SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the summary executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS),
        ],
    )

    # Check the service tests
    for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:8080'] + CLUSTER_TAGS
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:4040'] + CLUSTER_TAGS

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    proxy_cookie = {'proxy_cookie': 'foo'}
    fake_http.assert_requests(
        [
            RecordedRequest('GET', STANDALONE_APP_URL, {'cookies': None}),
            RecordedRequest('GET', _proxy_approved_url(STANDALONE_APP_URL), {'cookies': proxy_cookie}),
            RecordedRequest('GET', _proxy_approved_url(STANDALONE_APP_HTML_URL), {'cookies': proxy_cookie}),
            RecordedRequest('GET', _proxy_approved_url(SPARK_VERSION_URL), {'cookies': proxy_cookie}),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')),
                {'cookies': proxy_cookie},
            ),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages')),
                {'cookies': proxy_cookie},
            ),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors')),
                {'cookies': proxy_cookie},
            ),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')),
                {'cookies': proxy_cookie},
            ),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics')),
                {'cookies': proxy_cookie},
            ),
            RecordedRequest(
                'GET',
                _proxy_approved_url(join_url_dir(SPARK_APP_URL, 'metrics/json')),
                {'cookies': proxy_cookie},
            ),
        ]
    )
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_standalone_pre20(aggregator, dd_run_check, fake_http):
    _register_standalone_responses(fake_http, pre_20=True)
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG_PRE_20])
    dd_run_check(c)

    _assert(
        aggregator,
        [
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the running job metrics
            (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS),
            # Check the succeeded job metrics
            (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS),
            # Check the running stage metrics
            (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS),
            # Check the complete stage metrics
            (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS),
            # Check the driver metrics
            (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS),
            # Check the optional driver metrics
            (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the executor level metrics
            (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the optional executor level metrics
            (SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS),
            # Check the summary executor metrics
            (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS),
            # Check the optional summary executor metrics
            (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS),
            # Check the RDD metrics
            (SPARK_RDD_METRIC_VALUES, COMMON_TAGS),
            # Check the streaming statistics metrics
            (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS),
            # Check the structured streaming metrics
            (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS),
        ],
    )

    # Check the service tests
    for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:8080'] + CLUSTER_TAGS
    for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        assert sc.tags == ['url:http://localhost:4040'] + CLUSTER_TAGS

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_metadata(aggregator, datadog_agent, dd_run_check, fake_http):
    _register_standalone_responses(fake_http, pre_20=True)
    _register_fixture_response(fake_http, SPARK_VERSION_URL, 'version')
    c = SparkCheck(CHECK_NAME, {}, [STANDALONE_CONFIG_PRE_20])
    c.check_id = "test:123"
    dd_run_check(c)

    assert c._collect_version(SPARK_APP_URL, [])

    raw_version = "2.4.0"

    major, minor, patch = raw_version.split(".")

    version_metadata = {
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_disable_legacy_cluster_tags(aggregator, dd_run_check, fake_http):
    instance = MESOS_FILTERED_CONFIG.copy()
    instance['disable_legacy_cluster_tag'] = True

    _register_fixture_response(fake_http, MESOS_APP_URL, 'mesos_apps')
    c = SparkCheck('spark', {}, [instance])
    dd_run_check(c)

    for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
        assert sc.status == SparkCheck.OK
        # Only spark_cluster tag is present
        assert sc.tags == ['url:http://localhost:5050', 'spark_cluster:{}'.format(CLUSTER_NAME)]

    assert aggregator.metrics_asserted_pct == 100.0
    _assert_http_requests(fake_http)


@pytest.mark.unit
@pytest.mark.parametrize(
    "instance, register_responses, base_tags",
    [
        (DRIVER_CONFIG, _register_driver_responses, COMMON_TAGS + CUSTOM_TAGS),
        (YARN_CONFIG, _register_yarn_responses, COMMON_TAGS + CUSTOM_TAGS),
        (MESOS_CONFIG, _register_mesos_responses, COMMON_TAGS + CUSTOM_TAGS),
        (STANDALONE_CONFIG, _register_standalone_responses, COMMON_TAGS),
        (STANDALONE_CONFIG_PRE_20, _register_standalone_pre20_responses, COMMON_TAGS),
    ],
    ids=["driver", "yarn", "mesos", "standalone", "standalone_pre_20"],
)
def test_enable_query_name_tag_for_structured_streaming(
    aggregator, dd_run_check, fake_http, instance, register_responses, base_tags
):
    instance = instance.copy()
    instance['enable_query_name_tag'] = True

    register_responses(fake_http)
    c = SparkCheck('spark', {}, [instance])
    dd_run_check(c)

    for metric, value in SPARK_STRUCTURED_STREAMING_METRIC_VALUES.items():
        tags = base_tags
        if metric not in SPARK_STRUCTURED_STREAMING_METRIC_NO_TAGS:
            tags = base_tags + ["query_name:my_named_query"]

        aggregator.assert_metric(metric, value=value, tags=tags)

    for metric, value in SPARK_STRUCTURED_STREAMING_METRIC_PUNCTUATED_TAGS.items():
        tags = base_tags + ["query_name:my.app.punctuation"]

        aggregator.assert_metric(metric, value=value, tags=tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    _assert_http_requests(fake_http)


def test_do_not_crash_on_version_collection_failure(aggregator):
    def raise_request_error(*args: Any, **kwargs: Any) -> None:
        raise HTTPClientRequestError("test failure")

    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])

    with mock.patch.object(c, '_rest_request_to_json', new=raise_request_error):
        assert not c._collect_version(SPARK_APP_URL, [])

    assert aggregator.service_checks(SPARK_SERVICE_CHECK) == []


@pytest.mark.unit
def test_driver_startup_message_default_retries(aggregator, caplog, fake_http):
    """Default behavior (startup_wait_retries=3): retry 3 times then raise."""
    check = SparkCheck('spark', {}, [DRIVER_CONFIG])
    startup_message = "Spark is starting up. Please wait a while until it's ready."
    for _ in range(4):
        _register_response(fake_http, DRIVER_APP_URL, _invalid_json_response(startup_message))

    with caplog.at_level(logging.DEBUG):
        # First 3 attempts should return None (default is 3 retries)
        for i in range(3):
            result = check._rest_request_to_json(
                DRIVER_CONFIG['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, []
            )
            assert result is None, f"Attempt {i + 1} should return None"

        # 4th attempt should raise
        with pytest.raises(json.JSONDecodeError):
            check._rest_request_to_json(DRIVER_CONFIG['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    assert 'spark driver not ready yet' in caplog.text.lower()
    assert 'retries exhausted' in caplog.text.lower()

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(DRIVER_CONFIG['spark_url'])],
    )
    request = RecordedRequest('GET', DRIVER_APP_URL, {'cookies': None})
    fake_http.assert_requests([request] * 4)
    _assert_http_requests(fake_http)


@pytest.mark.unit
@pytest.mark.parametrize("retries_value", [0, -1, -5])
def test_driver_startup_message_disabled(aggregator, retries_value, fake_http):
    """When startup_wait_retries<=0, treat startup messages as errors immediately."""
    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = retries_value
    check = SparkCheck('spark', {}, [config])
    response = _invalid_json_response("Spark is starting up. Please wait a while until it's ready.")
    _register_response(fake_http, DRIVER_APP_URL, response)

    with pytest.raises(json.JSONDecodeError):
        check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(config['spark_url'])],
    )
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_driver_startup_message_limited_retries(aggregator, caplog, fake_http):
    """When startup_wait_retries>0, retry N times then raise."""
    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = 3
    check = SparkCheck('spark', {}, [config])
    startup_message = "Spark is starting up. Please wait a while until it's ready."
    for _ in range(4):
        _register_response(fake_http, DRIVER_APP_URL, _invalid_json_response(startup_message))

    with caplog.at_level(logging.DEBUG):
        # First 3 attempts should return None
        for i in range(3):
            result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
            assert result is None, f"Attempt {i + 1} should return None"

        # 4th attempt should raise
        with pytest.raises(json.JSONDecodeError):
            check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    assert 'attempt 1/3' in caplog.text.lower()
    assert 'attempt 3/3' in caplog.text.lower()
    assert 'retries exhausted' in caplog.text.lower()

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(config['spark_url'])],
    )
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_driver_startup_retry_counter_resets_on_success(caplog, fake_http):
    """Verify the retry counter resets after a successful JSON response."""
    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = 2
    check = SparkCheck('spark', {}, [config])
    startup_message = "Spark is starting up. Please wait a while until it's ready."
    responses = (
        _invalid_json_response(startup_message),
        _json_response([{"id": "app_001", "name": "TestApp"}]),
        _invalid_json_response(startup_message),
        _invalid_json_response(startup_message),
    )
    for response in responses:
        _register_response(fake_http, DRIVER_APP_URL, response)

    with caplog.at_level(logging.DEBUG):
        # Use 1 retry
        result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
        assert result is None
        assert check._startup_retry_count == 1

        # Successful response resets counter
        result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
        assert result == [{"id": "app_001", "name": "TestApp"}]
        assert check._startup_retry_count == 0

        # After reset, we should have 2 retries available again
        for _ in range(2):
            result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
            assert result is None

    request = RecordedRequest('GET', DRIVER_APP_URL, {'cookies': None})
    fake_http.assert_requests([request] * 4)
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_ssl(dd_run_check):
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_CONFIG])

    with pytest.raises(Exception, match="\\[SSL: CERTIFICATE_VERIFY_FAILED\\] certificate verify failed"):
        dd_run_check(c, extract_message=True)


@pytest.mark.unit
def test_ssl_no_verify(dd_run_check):
    # Disable ssl warning for self signed cert/no verify
    urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_NO_VERIFY_CONFIG])

    dd_run_check(c)


@pytest.mark.unit
def test_ssl_cert(dd_run_check):
    # Disable ssl warning for self signed cert/no verify
    urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_CERT_CONFIG])

    dd_run_check(c)


@pytest.mark.unit
def test_do_not_crash_on_single_app_failure(aggregator):
    first_app_url = 'http://first.example/'
    second_app_url = 'http://second.example/'
    running_apps = {
        'foo': ('FirstApp', first_app_url),
        'foo2': ('SecondApp', second_app_url),
    }
    requested_addresses: list[str] = []

    def rest_request_to_json(address: str, *args: Any, **kwargs: Any) -> list[Any]:
        requested_addresses.append(address)
        if address == first_app_url:
            raise Exception('first app disappeared')
        return []

    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])

    with (
        mock.patch.object(c, '_collect_version', new=lambda *args, **kwargs: True),
        mock.patch.object(c, '_rest_request_to_json', new=rest_request_to_json),
    ):
        assert c._get_spark_app_ids(running_apps, []) == {}

    assert requested_addresses == [first_app_url, second_app_url]
    assert aggregator.service_checks(SPARK_SERVICE_CHECK) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "instance,service_check,request_urls",
    [
        (DRIVER_CONFIG, "driver", [SPARK_VERSION_URL, DRIVER_APP_URL]),
        (YARN_CONFIG, "resource_manager", [YARN_APP_URL]),
        (MESOS_CONFIG, "mesos_master", [MESOS_APP_URL]),
        (STANDALONE_CONFIG, "standalone_master", [STANDALONE_APP_URL]),
        (STANDALONE_CONFIG_PRE_20, "standalone_master", [STANDALONE_APP_URL]),
    ],
    ids=["driver", "yarn", "mesos", "standalone", "standalone_pre_20"],
)
def test_no_running_apps(aggregator, dd_run_check, instance, service_check, request_urls, caplog, fake_http):
    for url in request_urls:
        _register_response(fake_http, url, _json_response({}))
    with caplog.at_level(logging.WARNING):
        dd_run_check(SparkCheck('spark', {}, [instance]))

    # no metrics sent in this case
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(
        'spark.{}.can_connect'.format(service_check),
        status=SparkCheck.OK,
        tags=['url:{}'.format(instance['spark_url'])] + CLUSTER_TAGS + instance.get('tags', []),
    )

    assert 'No running apps found. No metrics will be collected.' in caplog.text
    _assert_http_requests(fake_http)


@pytest.mark.unit
@pytest.mark.parametrize(
    "mock_response",
    [
        pytest.param(_invalid_json_response(""), id="Invalid JSON"),
        pytest.param(_status_response(404), id="property not found"),
        pytest.param(_status_response(500), id="Spark internal server error"),
    ],
)
@pytest.mark.parametrize(
    'property_url, missing_metrics',
    [
        pytest.param(YARN_SPARK_JOB_URL, SPARK_JOB_RUNNING_METRIC_VALUES, id='jobs'),
        pytest.param(YARN_SPARK_STAGE_URL, SPARK_STAGE_RUNNING_METRIC_VALUES, id='stages'),
        pytest.param(
            YARN_SPARK_EXECUTOR_URL,
            SPARK_EXECUTOR_METRIC_VALUES.keys() | SPARK_EXECUTOR_LEVEL_METRIC_VALUES.keys(),
            id='executors',
        ),
        pytest.param(YARN_SPARK_RDD_URL, SPARK_RDD_METRIC_VALUES, id='storage/rdd'),
        pytest.param(
            YARN_SPARK_STREAMING_STATISTICS_URL, SPARK_STREAMING_STATISTICS_METRIC_VALUES, id='streaming/statistics'
        ),
    ],
)
def test_yarn_no_json_for_app_properties(
    aggregator, dd_run_check, fake_http, mock_response, property_url, missing_metrics
):
    """
    In some yarn deployments apps stop exposing properties (such as jobs and stages) by the time we query them.
    In these cases we skip only the specific missing apps and metrics while collecting all others.
    """

    _register_fixture_response(fake_http, YARN_APP_URL, 'yarn_apps')
    _register_fixture_response(fake_http, YARN_SPARK_VERSION_URL, 'version')
    _register_response(
        fake_http,
        YARN_SPARK_APP_URL,
        _json_response(
            [
                {
                    "id": SPARK_APP_ID,
                    "name": "PySparkShell",
                    "attempts": [
                        {
                            "startTime": "2016-04-12T12:48:17.576GMT",
                            "endTime": "1969-12-31T23:59:59.999GMT",
                            "sparkUser": "",
                            "completed": False,
                        }
                    ],
                },
                {
                    "id": SPARK_APP2_ID,
                    "name": "PySparkShell2",
                    "attempts": [
                        {
                            "startTime": "2016-04-12T12:48:17.576GMT",
                            "endTime": "1969-12-31T23:59:59.999GMT",
                            "sparkUser": "",
                            "completed": False,
                        }
                    ],
                },
            ]
        ),
    )
    _register_application_responses(
        fake_http,
        YARN_APP_BASE_URL,
        overrides={property_url: mock_response},
    )
    _register_application_responses(fake_http, YARN_APP_BASE_URL, SPARK_APP2_ID)

    dd_run_check(SparkCheck('spark', {}, [YARN_CONFIG]))
    for m in missing_metrics:
        aggregator.assert_metric_has_tag(m, 'app_name:PySparkShell', count=0)
        aggregator.assert_metric_has_tag(m, 'app_name:PySparkShell2')
    _assert_http_requests(fake_http)


class StandaloneAppsResponseHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'rb') as f:
            self.wfile.write(f.read())


def run_ssl_server():
    cert_file = os.path.join(CERTIFICATE_DIR, 'server.pem')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file)

    httpd = BaseHTTPServer.HTTPServer((SSL_SERVER_ADDRESS, SSL_SERVER_PORT), StandaloneAppsResponseHandler)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=False)
    httpd.timeout = 5

    threading.Thread(target=httpd.handle_request).start()
    time.sleep(0.5)
    return httpd


SPARK_DRIVER_CLUSTER_TAGS = ['spark_cluster:{}'.format('SparkDriver'), 'cluster_name:{}'.format('SparkDriver')]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration_standalone(aggregator, dd_run_check):
    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])
    dd_run_check(c)

    expected_metric_values = (
        SPARK_JOB_RUNNING_METRIC_VALUES,
        SPARK_STAGE_RUNNING_METRIC_VALUES,
        SPARK_DRIVER_METRIC_VALUES,
        SPARK_STRUCTURED_STREAMING_METRIC_VALUES,
        SPARK_EXECUTOR_METRIC_VALUES,
    )
    optional_metric_values = (
        SPARK_STREAMING_STATISTICS_METRIC_VALUES,
        SPARK_DRIVER_OPTIONAL_METRIC_VALUES,
        SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES,
    )
    # Extract all keys
    expected_metrics = {k for j in expected_metric_values for k in j}
    optional_metrics = {k for j in optional_metric_values for k in j}
    # Check the running job metrics
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    for metric in optional_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check(
        'spark.standalone_master.can_connect',
        status=SparkCheck.OK,
        tags=['url:{}'.format('http://spark-master:8080')] + CLUSTER_TAGS,
    )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration_driver_1(aggregator, dd_run_check):
    c = SparkCheck('spark', {}, [INSTANCE_DRIVER_1])
    dd_run_check(c)

    all_metric_values = (
        SPARK_JOB_RUNNING_METRIC_VALUES,
        SPARK_STAGE_RUNNING_METRIC_VALUES,
        SPARK_DRIVER_METRIC_VALUES,
    )
    optional_metric_values = (
        SPARK_STREAMING_STATISTICS_METRIC_VALUES,
        SPARK_EXECUTOR_METRIC_VALUES,
        SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES,
        SPARK_DRIVER_OPTIONAL_METRIC_VALUES,
    )
    # Extract all keys
    expected_metrics = {k for j in all_metric_values for k in j}
    optional_metrics = {k for j in optional_metric_values for k in j}

    # Check the running job metrics
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    for metric in optional_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check(
        'spark.driver.can_connect',
        status=SparkCheck.OK,
        tags=['url:{}'.format('http://spark-app-1:4040')] + SPARK_DRIVER_CLUSTER_TAGS,
    )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration_driver_2(aggregator, dd_run_check):
    c = SparkCheck('spark', {}, [INSTANCE_DRIVER_2])
    dd_run_check(c)

    all_metric_values = (
        SPARK_DRIVER_METRIC_VALUES,
        SPARK_STRUCTURED_STREAMING_METRIC_VALUES,
    )
    optional_metric_values = (
        SPARK_STAGE_RUNNING_METRIC_VALUES,
        SPARK_EXECUTOR_METRIC_VALUES,
        SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES,
        SPARK_DRIVER_OPTIONAL_METRIC_VALUES,
        SPARK_JOB_RUNNING_METRIC_VALUES,
        SPARK_JOB_SUCCEEDED_METRIC_VALUES,
    )
    # Extract all keys
    expected_metrics = {k for j in all_metric_values for k in j}
    optional_metrics = {k for j in optional_metric_values for k in j}

    # Check the running job metrics
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    for metric in optional_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check(
        'spark.driver.can_connect',
        status=SparkCheck.OK,
        tags=['url:{}'.format('http://spark-app-2:4050')] + SPARK_DRIVER_CLUSTER_TAGS,
    )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_debounce_connection_failure(aggregator, dd_run_check, caplog, fake_http):
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    for _ in range(2):
        _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientConnectionError("Connection refused"))
    c = SparkCheck('spark', {}, [instance])

    # First run: expect warning, no CRITICAL check
    with caplog.at_level(logging.WARNING):
        dd_run_check(c)

    assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text

    # Verify no CRITICAL check sent for spark.driver.can_connect
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0

    # Second run: expect CRITICAL (wrapped by dd_run_check as Exception)
    with pytest.raises(Exception) as excinfo:
        dd_run_check(c)

    assert "Connection refused" in str(excinfo.value)

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 1
    assert service_checks[0].status == SparkCheck.CRITICAL
    fake_http.assert_requests(
        [
            RecordedRequest('GET', SPARK_VERSION_URL, {'cookies': None}),
            RecordedRequest('GET', SPARK_VERSION_URL, {'cookies': None}),
            RecordedRequest('GET', DRIVER_APP_URL, {'cookies': None}),
        ]
    )
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_connection_failure_non_k8s(aggregator, dd_run_check, fake_http):
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', []))

    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientConnectionError("Connection refused"))
    c = SparkCheck('spark', {}, [instance])

    with pytest.raises(Exception) as excinfo:
        dd_run_check(c)

    assert "Connection refused" in str(excinfo.value)

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 1
    assert service_checks[0].status == SparkCheck.CRITICAL
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_malformed_header_still_reports_critical(aggregator, dd_run_check, fake_http):
    message = 'Content-Length contained multiple unmatching values'
    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientRequestError(message))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientRequestError(message))
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', []))
    c = SparkCheck('spark', {}, [instance])

    with pytest.raises(Exception, match=message):
        dd_run_check(c)

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 1
    assert service_checks[0].status == SparkCheck.CRITICAL
    assert service_checks[0].message == message
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_debounce_connection_failure_terminal_phase(aggregator, dd_run_check, caplog, fake_http):
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Failed']

    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientConnectionError("Connection refused"))
    c = SparkCheck('spark', {}, [instance])

    with caplog.at_level(logging.DEBUG):
        dd_run_check(c)

    assert "Pod phase is terminal, suppressing request error" in caplog.text

    # Expect NO service check because we suppress errors for failed pods
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_debounce_connection_recovery(aggregator, dd_run_check, caplog, fake_http):
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    c = SparkCheck('spark', {}, [instance])

    # 1. Fail (Debounce)
    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    with caplog.at_level(logging.WARNING):
        dd_run_check(c)

    assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text
    # Verify no CRITICAL check sent
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0
    _assert_http_requests(fake_http)

    caplog.clear()
    aggregator.reset()

    # 2. Success (Reset)
    _register_driver_responses(fake_http)
    dd_run_check(c)

    # Verify success
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) > 0
    assert service_checks[0].status == SparkCheck.OK

    # Verify internal state was reset
    assert c._connection_error_seen is False
    _assert_http_requests(fake_http)

    caplog.clear()
    aggregator.reset()

    # 3. Fail (Debounce again)
    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    with caplog.at_level(logging.WARNING):
        dd_run_check(c)

    assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text
    # Verify no CRITICAL check sent
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0
    _assert_http_requests(fake_http)


@pytest.mark.unit
@pytest.mark.parametrize(
    "pod_phase",
    ["Failed", "Succeeded", "Unknown"],
)
def test_debounce_connection_failure_all_terminal_phases(aggregator, dd_run_check, caplog, fake_http, pod_phase):
    """Test that all terminal pod phases suppress connection errors."""
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:{}'.format(pod_phase)]

    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("Connection refused"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientConnectionError("Connection refused"))
    c = SparkCheck('spark', {}, [instance])

    with caplog.at_level(logging.DEBUG):
        dd_run_check(c)

    assert "Pod phase is terminal, suppressing request error" in caplog.text

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_debounce_no_route_to_host(aggregator, dd_run_check, caplog, fake_http):
    """Test that 'No route to host' errors are also debounced."""
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectionError("No route to host"))
    c = SparkCheck('spark', {}, [instance])

    # First run: expect warning, no CRITICAL check
    with caplog.at_level(logging.WARNING):
        dd_run_check(c)

    assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_read_timeout_terminal_phase_suppressed(aggregator, dd_run_check, caplog, fake_http):
    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientReadTimeoutError("Read timed out"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientReadTimeoutError("Read timed out"))
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Failed']
    c = SparkCheck('spark', {}, [instance])

    with caplog.at_level(logging.DEBUG):
        dd_run_check(c)

    assert "Pod phase is terminal, suppressing request error" in caplog.text
    assert aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK) == []
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_connect_timeout_terminal_phase_still_alerts(aggregator, dd_run_check, fake_http):
    _register_response(fake_http, SPARK_VERSION_URL, HTTPClientConnectTimeoutError("Connection timed out"))
    _register_response(fake_http, DRIVER_APP_URL, HTTPClientConnectTimeoutError("Connection timed out"))
    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Failed']
    c = SparkCheck('spark', {}, [instance])

    with pytest.raises(Exception, match='Connection timed out'):
        dd_run_check(c)

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 1
    assert service_checks[0].status == SparkCheck.CRITICAL
    _assert_http_requests(fake_http)


@pytest.mark.unit
def test_get_pod_phase():
    """Test _get_pod_phase static method."""
    assert SparkCheck._get_pod_phase(['pod_phase:Running']) == 'running'
    assert SparkCheck._get_pod_phase(['pod_phase:Failed']) == 'failed'
    assert SparkCheck._get_pod_phase(['other:tag', 'pod_phase:Succeeded']) == 'succeeded'
    assert SparkCheck._get_pod_phase(['other:tag']) is None
    assert SparkCheck._get_pod_phase(None) is None
    assert SparkCheck._get_pod_phase([]) is None
