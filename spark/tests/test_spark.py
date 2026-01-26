# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import ssl
import threading
import time
from http import server as BaseHTTPServer
from urllib.parse import parse_qsl, unquote_plus, urlencode, urljoin, urlparse, urlunparse

import mock
import pytest
import urllib3
from requests import ConnectionError, RequestException

from datadog_checks.dev.http import MockResponse
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

YARN_APP_ID_TAG = ['app_id:' + SPARK_APP_ID]
SPARK_APP_ID_TAG = ['app_id:' + SPARK_APP_ID]
SPARK_APP_ID_TAG_PRE20 = ['app_id:' + APP_NAME]
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


class Url(object):
    """A url object that can be compared with other url orbjects
    without regard to the vagaries of encoding, escaping, and ordering
    of parameters in query strings."""

    def __init__(self, url):
        parts = urlparse(url)
        _query = frozenset(parse_qsl(parts.query))
        _path = unquote_plus(parts.path)
        parts = parts._replace(query=_query, path=_path)
        self.parts = parts

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


# PATH to Spark Version
VERSION_PATH = Url(urljoin(SPARK_APP_URL, VERSION_PATH))

# YARN Service URLs
YARN_APP_URL = Url(urljoin(SPARK_YARN_URL, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=SPARK')
YARN_SPARK_APP_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH))
YARN_SPARK_JOB_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
YARN_SPARK_STAGE_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
YARN_SPARK_EXECUTOR_URL = Url(
    join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
)
YARN_SPARK_RDD_URL = Url(
    join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')
)
YARN_SPARK_STREAMING_STATISTICS_URL = Url(
    join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics')
)
YARN_SPARK_METRICS_JSON_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, 'metrics/json'))

# Mesos Service URLs
MESOS_APP_URL = Url(urljoin(SPARK_MESOS_URL, MESOS_APPS_PATH))
MESOS_SPARK_APP_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH))
MESOS_SPARK_JOB_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
MESOS_SPARK_STAGE_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
MESOS_SPARK_EXECUTOR_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
MESOS_SPARK_RDD_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))
MESOS_SPARK_STREAMING_STATISTICS_URL = Url(
    join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics')
)
MESOS_SPARK_METRICS_JSON_URL = Url(join_url_dir(SPARK_APP_URL, 'metrics/json'))

# Driver Service URLs
DRIVER_APP_URL = Url(urljoin(SPARK_APP_URL, SPARK_REST_PATH))
DRIVER_SPARK_APP_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH))
DRIVER_SPARK_JOB_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
DRIVER_SPARK_STAGE_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
DRIVER_SPARK_EXECUTOR_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
DRIVER_SPARK_RDD_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))
DRIVER_SPARK_STREAMING_STATISTICS_URL = Url(
    join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics')
)
DRIVER_SPARK_METRICS_JSON_URL = Url(join_url_dir(SPARK_APP_URL, 'metrics/json'))

# Spark Standalone Service URLs
STANDALONE_APP_URL = Url(urljoin(STANDALONE_URL, STANDALONE_APPS_PATH))
STANDALONE_APP_HTML_URL = Url(urljoin(STANDALONE_URL, STANDALONE_APP_PATH_HTML) + '?appId=' + SPARK_APP_ID)
STANDALONE_SPARK_APP_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH))
STANDALONE_SPARK_JOB_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
STANDALONE_SPARK_STAGE_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
STANDALONE_SPARK_EXECUTOR_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
STANDALONE_SPARK_RDD_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))
STANDALONE_SPARK_STREAMING_STATISTICS_URL = Url(
    join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'streaming/statistics')
)
STANDALONE_SPARK_METRICS_JSON_URL = Url(join_url_dir(SPARK_APP_URL, 'metrics/json'))

STANDALONE_SPARK_JOB_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'jobs'))
STANDALONE_SPARK_STAGE_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'stages'))
STANDALONE_SPARK_EXECUTOR_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'executors'))
STANDALONE_SPARK_RDD_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'storage/rdd'))
STANDALONE_SPARK_STREAMING_STATISTICS_URL_PRE20 = Url(
    join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'streaming/statistics')
)
STANDALONE_SPARK_METRICS_JSON_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, 'metrics/json'))

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')

DEFAULT_RESPONSES = {
    '/jobs': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'job_metrics')),
    '/stages': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'stage_metrics')),
    '/executors': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'executor_metrics')),
    '/storage/rdd': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'rdd_metrics')),
    '/streaming/statistics': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'streaming_statistics')),
    '/metrics/json': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'metrics_json')),
    '/api/v1/version': MockResponse(file_path=os.path.join(FIXTURE_DIR, 'version')),
}


def get_default_mock(url):
    for k, v in DEFAULT_RESPONSES.items():
        if url.endswith(k):
            return v
    raise KeyError(f"{url} does not match any response fixtures.")


def yarn_requests_get_mock(session, url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == YARN_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'yarn_apps'))
    elif arg_url == YARN_SPARK_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps'))
    return get_default_mock(url)


def yarn_requests_auth_mock(session, url, *args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return yarn_requests_get_mock(session, url, *args, **kwargs)


def mesos_requests_get_mock(session, url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == MESOS_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'mesos_apps'))
    elif arg_url == MESOS_SPARK_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps'))
    elif arg_url == MESOS_SPARK_JOB_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'job_metrics'))
    elif arg_url == MESOS_SPARK_STAGE_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'stage_metrics'))
    elif arg_url == MESOS_SPARK_EXECUTOR_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'executor_metrics'))
    elif arg_url == MESOS_SPARK_RDD_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'rdd_metrics'))
    elif arg_url == MESOS_SPARK_STREAMING_STATISTICS_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'streaming_statistics'))
    elif arg_url == MESOS_SPARK_METRICS_JSON_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'metrics_json'))


def driver_requests_get_mock(session, url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == DRIVER_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps'))
    elif arg_url == DRIVER_SPARK_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps'))
    elif arg_url == DRIVER_SPARK_JOB_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'job_metrics'))
    elif arg_url == DRIVER_SPARK_STAGE_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'stage_metrics'))
    elif arg_url == DRIVER_SPARK_EXECUTOR_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'executor_metrics'))
    elif arg_url == DRIVER_SPARK_RDD_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'rdd_metrics'))
    elif arg_url == DRIVER_SPARK_STREAMING_STATISTICS_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'streaming_statistics'))
    elif arg_url == DRIVER_SPARK_METRICS_JSON_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'metrics_json'))


def standalone_requests_get_mock(session, url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == STANDALONE_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_standalone_apps'))
    elif arg_url == STANDALONE_APP_HTML_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_standalone_app'))
    elif arg_url == STANDALONE_SPARK_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps'))
    elif arg_url == STANDALONE_SPARK_JOB_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'job_metrics'))
    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'stage_metrics'))
    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'executor_metrics'))
    elif arg_url == STANDALONE_SPARK_RDD_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'rdd_metrics'))
    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'streaming_statistics'))
    elif arg_url == STANDALONE_SPARK_METRICS_JSON_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'metrics_json'))


def standalone_requests_pre20_get_mock(session, url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == STANDALONE_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_standalone_apps'))
    elif arg_url == STANDALONE_APP_HTML_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_standalone_app'))
    elif arg_url == STANDALONE_SPARK_APP_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'spark_apps_pre20'))
    elif arg_url == STANDALONE_SPARK_JOB_URL:
        return MockResponse(status_code=404)
    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        return MockResponse(status_code=404)
    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        return MockResponse(status_code=404)
    elif arg_url == STANDALONE_SPARK_RDD_URL:
        return MockResponse(status_code=404)
    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL:
        return MockResponse(status_code=404)
    elif arg_url == STANDALONE_SPARK_JOB_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'job_metrics'))
    elif arg_url == STANDALONE_SPARK_STAGE_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'stage_metrics'))
    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'executor_metrics'))
    elif arg_url == STANDALONE_SPARK_RDD_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'rdd_metrics'))
    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'streaming_statistics'))
    elif arg_url == VERSION_PATH:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'version'))
    elif arg_url == STANDALONE_SPARK_METRICS_JSON_URL_PRE20:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'metrics_json'))


def proxy_with_warning_page_mock(session, url, *args, **kwargs):
    cookies = kwargs.get('cookies') or {}
    proxy_cookie = cookies.get('proxy_cookie')
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    if proxy_cookie and query.get('proxyapproved') == 'true':
        del query['proxyapproved']
        url_parts[4] = urlencode(query)
        return standalone_requests_get_mock(session, urlunparse(url_parts), *args[1:], **kwargs)
    else:
        # Display the html warning page with the redirect link
        query['proxyapproved'] = 'true'
        url_parts[4] = urlencode(query)
        with open(os.path.join(FIXTURE_DIR, 'html_warning_page'), 'r') as f:
            body = f.read().replace('$REDIRECT_URL$', urlunparse(url_parts))
            return MockResponse(body, cookies={'proxy_cookie': 'foo'})


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
def test_yarn(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', yarn_requests_get_mock):
        c = SparkCheck('spark', {}, [YARN_CONFIG])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG,
                ),
                # Check the summary executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
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


@pytest.mark.unit
def test_auth_yarn(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', yarn_requests_auth_mock):
        c = SparkCheck('spark', {}, [YARN_AUTH_CONFIG])
        dd_run_check(c)

        tags = ['url:http://localhost:8088'] + CUSTOM_TAGS + CLUSTER_TAGS
        tags.sort()

        for sc in aggregator.service_checks(YARN_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            sc.tags.sort()
            assert sc.tags == tags

        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            sc.tags.sort()
            assert sc.tags == tags


@pytest.mark.unit
def test_mesos(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', mesos_requests_get_mock):
        c = SparkCheck('spark', {}, [MESOS_CONFIG])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG,
                ),
                # Check the summary executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the streaming statistics metrics,
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
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


@pytest.mark.unit
def test_mesos_filter(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', mesos_requests_get_mock):
        c = SparkCheck('spark', {}, [MESOS_FILTERED_CONFIG])
        dd_run_check(c)

        for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:5050'] + CLUSTER_TAGS

        assert aggregator.metrics_asserted_pct == 100.0


@pytest.mark.unit
def test_driver_unit(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', driver_requests_get_mock):
        c = SparkCheck('spark', {}, [DRIVER_CONFIG])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG,
                ),
                # Check the summary executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
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


@pytest.mark.unit
def test_standalone_unit(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', standalone_requests_get_mock):
        c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG,
                ),
                # Check the executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
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


@pytest.mark.unit
def test_standalone_stage_disabled_unit(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', standalone_requests_get_mock):
        c = SparkCheck('spark', {}, [STANDALONE_CONFIG_STAGE_DISABLED])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_NO_STAGE_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG,
                ),
                # Check the executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
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


@pytest.mark.unit
def test_standalone_unit_with_proxy_warning_page(aggregator, dd_run_check):
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
    with mock.patch('requests.Session.get', proxy_with_warning_page_mock):
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG,
                ),
                # Check the summary executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG),
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


@pytest.mark.unit
def test_standalone_pre20(aggregator, dd_run_check):
    with mock.patch('requests.Session.get', standalone_requests_pre20_get_mock):
        c = SparkCheck('spark', {}, [STANDALONE_CONFIG_PRE_20])
        dd_run_check(c)

        _assert(
            aggregator,
            [
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the running job metrics
                (SPARK_JOB_RUNNING_METRIC_VALUES, SPARK_JOB_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the succeeded job metrics
                (SPARK_JOB_SUCCEEDED_METRIC_VALUES, SPARK_JOB_SUCCEEDED_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the running stage metrics
                (SPARK_STAGE_RUNNING_METRIC_VALUES, SPARK_STAGE_RUNNING_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the complete stage metrics
                (SPARK_STAGE_COMPLETE_METRIC_VALUES, SPARK_STAGE_COMPLETE_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the driver metrics
                (SPARK_DRIVER_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the optional driver metrics
                (SPARK_DRIVER_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the executor level metrics
                (SPARK_EXECUTOR_LEVEL_METRIC_VALUES, SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the optional executor level metrics
                (
                    SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES,
                    SPARK_EXECUTOR_LEVEL_METRIC_TAGS + SPARK_APP_ID_TAG_PRE20,
                ),
                # Check the summary executor metrics
                (SPARK_EXECUTOR_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the optional summary executor metrics
                (SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the RDD metrics
                (SPARK_RDD_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the streaming statistics metrics
                (SPARK_STREAMING_STATISTICS_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
                # Check the structured streaming metrics
                (SPARK_STRUCTURED_STREAMING_METRIC_VALUES, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
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


@pytest.mark.unit
def test_metadata(aggregator, datadog_agent, dd_run_check):
    with mock.patch('requests.Session.get', standalone_requests_pre20_get_mock):
        c = SparkCheck(CHECK_NAME, {}, [STANDALONE_CONFIG_PRE_20])
        c.check_id = "test:123"
        dd_run_check(c)

        c._collect_version(SPARK_APP_URL, None)

        raw_version = "2.4.0"

        major, minor, patch = raw_version.split(".")

        version_metadata = {
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': raw_version,
        }

        datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.unit
def test_disable_legacy_cluster_tags(aggregator, dd_run_check):
    instance = MESOS_FILTERED_CONFIG
    instance['disable_legacy_cluster_tag'] = True

    with mock.patch('requests.Session.get', mesos_requests_get_mock):
        c = SparkCheck('spark', {}, [instance])
        dd_run_check(c)

        for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            # Only spark_cluster tag is present
            assert sc.tags == ['url:http://localhost:5050', 'spark_cluster:{}'.format(CLUSTER_NAME)]

        assert aggregator.metrics_asserted_pct == 100.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "instance, requests_get_mock, base_tags",
    [
        (DRIVER_CONFIG, driver_requests_get_mock, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
        (YARN_CONFIG, yarn_requests_get_mock, COMMON_TAGS + CUSTOM_TAGS + YARN_APP_ID_TAG),
        (MESOS_CONFIG, mesos_requests_get_mock, COMMON_TAGS + CUSTOM_TAGS + SPARK_APP_ID_TAG),
        (STANDALONE_CONFIG, standalone_requests_get_mock, COMMON_TAGS + SPARK_APP_ID_TAG),
        (STANDALONE_CONFIG_PRE_20, standalone_requests_pre20_get_mock, COMMON_TAGS + SPARK_APP_ID_TAG_PRE20),
    ],
    ids=["driver", "yarn", "mesos", "standalone", "standalone_pre_20"],
)
def test_enable_query_name_tag_for_structured_streaming(
    aggregator, dd_run_check, instance, requests_get_mock, base_tags
):
    instance['enable_query_name_tag'] = True

    with mock.patch('requests.Session.get', requests_get_mock):
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


def test_do_not_crash_on_version_collection_failure():
    running_apps = {'foo': ('bar', 'http://foo.bar/'), 'foo2': ('bar', 'http://foo.bar/')}
    rest_requests_to_json = mock.MagicMock(side_effect=[RequestException, []])

    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])

    with mock.patch.object(c, '_rest_request_to_json', rest_requests_to_json):
        # ensure no exception is raised by calling collect_version
        assert not c._collect_version(running_apps, [])


@pytest.mark.unit
def test_driver_startup_message_default_retries(aggregator, caplog):
    """Default behavior (startup_wait_retries=3): retry 3 times then raise."""
    from simplejson import JSONDecodeError

    check = SparkCheck('spark', {}, [DRIVER_CONFIG])
    response = MockResponse(content="Spark is starting up. Please wait a while until it's ready.")

    with caplog.at_level(logging.DEBUG):
        with mock.patch.object(check, '_rest_request', return_value=response):
            # First 3 attempts should return None (default is 3 retries)
            for i in range(3):
                result = check._rest_request_to_json(
                    DRIVER_CONFIG['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, []
                )
                assert result is None, f"Attempt {i + 1} should return None"

            # 4th attempt should raise
            with pytest.raises(JSONDecodeError):
                check._rest_request_to_json(DRIVER_CONFIG['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    assert 'spark driver not ready yet' in caplog.text.lower()
    assert 'retries exhausted' in caplog.text.lower()

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(DRIVER_CONFIG['spark_url'])],
    )


@pytest.mark.unit
@pytest.mark.parametrize("retries_value", [0, -1, -5])
def test_driver_startup_message_disabled(aggregator, retries_value):
    """When startup_wait_retries<=0, treat startup messages as errors immediately."""
    from simplejson import JSONDecodeError

    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = retries_value
    check = SparkCheck('spark', {}, [config])
    response = MockResponse(content="Spark is starting up. Please wait a while until it's ready.")

    with mock.patch.object(check, '_rest_request', return_value=response):
        with pytest.raises(JSONDecodeError):
            check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(config['spark_url'])],
    )


@pytest.mark.unit
def test_driver_startup_message_limited_retries(aggregator, caplog):
    """When startup_wait_retries>0, retry N times then raise."""
    from simplejson import JSONDecodeError

    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = 3
    check = SparkCheck('spark', {}, [config])
    response = MockResponse(content="Spark is starting up. Please wait a while until it's ready.")

    with caplog.at_level(logging.DEBUG):
        with mock.patch.object(check, '_rest_request', return_value=response):
            # First 3 attempts should return None
            for i in range(3):
                result = check._rest_request_to_json(
                    config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, []
                )
                assert result is None, f"Attempt {i + 1} should return None"

            # 4th attempt should raise
            with pytest.raises(JSONDecodeError):
                check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])

    assert 'attempt 1/3' in caplog.text.lower()
    assert 'attempt 3/3' in caplog.text.lower()
    assert 'retries exhausted' in caplog.text.lower()

    aggregator.assert_service_check(
        SPARK_DRIVER_SERVICE_CHECK,
        status=SparkCheck.CRITICAL,
        tags=['url:{}'.format(config['spark_url'])],
    )


@pytest.mark.unit
def test_driver_startup_retry_counter_resets_on_success(caplog):
    """Verify the retry counter resets after a successful JSON response."""
    config = DRIVER_CONFIG.copy()
    config['startup_wait_retries'] = 2
    check = SparkCheck('spark', {}, [config])
    startup_response = MockResponse(content="Spark is starting up. Please wait a while until it's ready.")
    success_response = MockResponse(json_data=[{"id": "app_001", "name": "TestApp"}])

    with caplog.at_level(logging.DEBUG):
        with mock.patch.object(check, '_rest_request', return_value=startup_response):
            # Use 1 retry
            result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
            assert result is None
            assert check._startup_retry_count == 1

        # Successful response resets counter
        with mock.patch.object(check, '_rest_request', return_value=success_response):
            result = check._rest_request_to_json(config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, [])
            assert result == [{"id": "app_001", "name": "TestApp"}]
            assert check._startup_retry_count == 0

        # After reset, we should have 2 retries available again
        with mock.patch.object(check, '_rest_request', return_value=startup_response):
            for _ in range(2):
                result = check._rest_request_to_json(
                    config['spark_url'], SPARK_REST_PATH, SPARK_DRIVER_SERVICE_CHECK, []
                )
                assert result is None


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
def test_do_not_crash_on_single_app_failure():
    running_apps = {'foo': ('bar', 'http://foo.bar/'), 'foo2': ('bar', 'http://foo.bar/')}
    results = []
    rest_requests_to_json = mock.MagicMock(side_effect=[Exception, results])
    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])

    with mock.patch.object(c, '_rest_request_to_json', rest_requests_to_json), mock.patch.object(c, '_collect_version'):
        c._get_spark_app_ids(running_apps, [])
        assert rest_requests_to_json.call_count == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "instance,service_check",
    [
        (DRIVER_CONFIG, "driver"),
        (YARN_CONFIG, "resource_manager"),
        (MESOS_CONFIG, "mesos_master"),
        (STANDALONE_CONFIG, "standalone_master"),
        (STANDALONE_CONFIG_PRE_20, "standalone_master"),
    ],
    ids=["driver", "yarn", "mesos", "standalone", "standalone_pre_20"],
)
def test_no_running_apps(aggregator, dd_run_check, instance, service_check, caplog):
    with mock.patch('requests.Session.get', return_value=MockResponse("{}")):
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


@pytest.mark.unit
@pytest.mark.parametrize(
    "mock_response",
    [
        pytest.param(MockResponse(content=""), id="Invalid JSON"),  # this triggers json parsing error,
        pytest.param(MockResponse(status_code=404), id="property not found"),
        pytest.param(MockResponse(status_code=500), id="Spark internal server error"),  # reported by users in the wild
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
    aggregator, dd_run_check, mocker, mock_response, property_url, missing_metrics
):
    """
    In some yarn deployments apps stop exposing properties (such as jobs and stages) by the time we query them.
    In these cases we skip only the specific missing apps and metrics while collecting all others.
    """

    def get_without_json(session, url, *args, **kwargs):
        arg_url = Url(url)
        if arg_url == property_url:
            return mock_response
        elif arg_url == YARN_SPARK_APP_URL:
            return MockResponse(
                json_data=[
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
            )
        else:
            return yarn_requests_get_mock(session, url, *args, **kwargs)

    mocker.patch('requests.Session.get', get_without_json)
    dd_run_check(SparkCheck('spark', {}, [YARN_CONFIG]))
    for m in missing_metrics:
        aggregator.assert_metric_has_tag(m, 'app_name:PySparkShell', count=0)
        aggregator.assert_metric_has_tag(m, 'app_name:PySparkShell2')


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
def test_debounce_connection_failure(aggregator, dd_run_check, caplog):
    # Mock connection failure
    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("Connection refused")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
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


@pytest.mark.unit
def test_connection_failure_non_k8s(aggregator, dd_run_check):
    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("Connection refused")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', []))

    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        c = SparkCheck('spark', {}, [instance])

        with pytest.raises(Exception) as excinfo:
            dd_run_check(c)

        assert "Connection refused" in str(excinfo.value)

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 1
    assert service_checks[0].status == SparkCheck.CRITICAL


@pytest.mark.unit
def test_debounce_connection_failure_terminal_phase(aggregator, dd_run_check, caplog):
    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("Connection refused")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Failed']

    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        c = SparkCheck('spark', {}, [instance])

        with caplog.at_level(logging.DEBUG):
            dd_run_check(c)

        assert "Pod phase is terminal, suppressing request error" in caplog.text

    # Expect NO service check because we suppress errors for failed pods
    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0


@pytest.mark.unit
def test_debounce_connection_recovery(aggregator, dd_run_check, caplog):
    # Mock connection failure
    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("Connection refused")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    c = SparkCheck('spark', {}, [instance])

    # 1. Fail (Debounce)
    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        with caplog.at_level(logging.WARNING):
            dd_run_check(c)

        assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text
        # Verify no CRITICAL check sent
        service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
        assert len(service_checks) == 0

    caplog.clear()
    aggregator.reset()

    # 2. Success (Reset)
    with mock.patch('requests.Session.get', driver_requests_get_mock):
        dd_run_check(c)

        # Verify success
        service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
        assert len(service_checks) > 0
        assert service_checks[0].status == SparkCheck.OK

        # Verify internal state was reset
        assert c._connection_error_seen is False

    caplog.clear()
    aggregator.reset()

    # 3. Fail (Debounce again)
    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        with caplog.at_level(logging.WARNING):
            dd_run_check(c)

        assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text
        # Verify no CRITICAL check sent
        service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
        assert len(service_checks) == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "pod_phase",
    ["Failed", "Succeeded", "Unknown"],
)
def test_debounce_connection_failure_all_terminal_phases(aggregator, dd_run_check, caplog, pod_phase):
    """Test that all terminal pod phases suppress connection errors."""

    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("Connection refused")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:{}'.format(pod_phase)]

    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        c = SparkCheck('spark', {}, [instance])

        with caplog.at_level(logging.DEBUG):
            dd_run_check(c)

        assert "Pod phase is terminal, suppressing request error" in caplog.text

    service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
    assert len(service_checks) == 0


@pytest.mark.unit
def test_debounce_no_route_to_host(aggregator, dd_run_check, caplog):
    """Test that 'No route to host' errors are also debounced."""

    def connection_failure_mock(*args, **kwargs):
        raise ConnectionError("No route to host")

    instance = DRIVER_CONFIG.copy()
    instance['tags'] = list(instance.get('tags', [])) + ['pod_phase:Running']

    with mock.patch('requests.Session.get', side_effect=connection_failure_mock):
        c = SparkCheck('spark', {}, [instance])

        # First run: expect warning, no CRITICAL check
        with caplog.at_level(logging.WARNING):
            dd_run_check(c)

        assert "Connection failed. Suppressing error once to ensure driver is running" in caplog.text

        service_checks = aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK)
        assert len(service_checks) == 0


@pytest.mark.unit
def test_get_pod_phase():
    """Test _get_pod_phase static method."""
    assert SparkCheck._get_pod_phase(['pod_phase:Running']) == 'running'
    assert SparkCheck._get_pod_phase(['pod_phase:Failed']) == 'failed'
    assert SparkCheck._get_pod_phase(['other:tag', 'pod_phase:Succeeded']) == 'succeeded'
    assert SparkCheck._get_pod_phase(['other:tag']) is None
    assert SparkCheck._get_pod_phase(None) is None
    assert SparkCheck._get_pod_phase([]) is None
