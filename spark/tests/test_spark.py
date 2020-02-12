# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import ssl
import threading
import time

import mock
import pytest
import requests
import urllib3
from requests import RequestException
from six import iteritems
from six.moves import BaseHTTPServer
from six.moves.urllib.parse import parse_qsl, unquote_plus, urlencode, urljoin, urlparse, urlunparse

from datadog_checks.base import ensure_unicode
from datadog_checks.spark import SparkCheck

from .common import HOST, INSTANCE_DRIVER, INSTANCE_STANDALONE

# IDs
YARN_APP_ID = 'application_1459362484344_0011'
SPARK_APP_ID = 'app_001'
CLUSTER_NAME = 'SparkCluster'
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

STANDALONE_SPARK_JOB_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'jobs'))
STANDALONE_SPARK_STAGE_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'stages'))
STANDALONE_SPARK_EXECUTOR_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'executors'))
STANDALONE_SPARK_RDD_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'storage/rdd'))
STANDALONE_SPARK_STREAMING_STATISTICS_URL_PRE20 = Url(
    join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'streaming/statistics')
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')


class MockedResponse:
    def __init__(self, json_data, status_code, cookies=None):
        self.json_data = json_data
        self.status_code = status_code
        self.cookies = cookies

    @property
    def text(self):
        return ensure_unicode(self.json_data)

    def json(self):
        return json.loads(self.json_data)

    def raise_for_status(self):
        return True


def yarn_requests_get_mock(url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == YARN_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'yarn_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == YARN_SPARK_STREAMING_STATISTICS_URL:
        with open(os.path.join(FIXTURE_DIR, 'streaming_statistics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)


def yarn_requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return yarn_requests_get_mock(*args, **kwargs)


def mesos_requests_get_mock(url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == MESOS_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'mesos_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == MESOS_SPARK_STREAMING_STATISTICS_URL:
        with open(os.path.join(FIXTURE_DIR, 'streaming_statistics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)


def driver_requests_get_mock(url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == DRIVER_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == DRIVER_SPARK_STREAMING_STATISTICS_URL:
        with open(os.path.join(FIXTURE_DIR, 'streaming_statistics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)


def standalone_requests_get_mock(url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == STANDALONE_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_APP_HTML_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_app'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL:
        with open(os.path.join(FIXTURE_DIR, 'streaming_statistics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)


def standalone_requests_pre20_get_mock(url, *args, **kwargs):
    arg_url = Url(url)

    if arg_url == STANDALONE_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_APP_HTML_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_app'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps_pre20'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_JOB_URL:
        return MockedResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        return MockedResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        return MockedResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_RDD_URL:
        return MockedResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL:
        return MockedResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_JOB_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STAGE_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_RDD_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STREAMING_STATISTICS_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'streaming_statistics'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)

    elif arg_url == VERSION_PATH:
        with open(os.path.join(FIXTURE_DIR, 'version'), 'rb') as f:
            body = f.read()
            return MockedResponse(body, 200)


def proxy_with_warning_page_mock(url, *args, **kwargs):
    cookies = kwargs.get('cookies') or {}
    proxy_cookie = cookies.get('proxy_cookie')
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    if proxy_cookie and query.get('proxyapproved') == 'true':
        del query['proxyapproved']
        url_parts[4] = urlencode(query)
        return standalone_requests_get_mock(urlunparse(url_parts), *args[1:], **kwargs)
    else:
        # Display the html warning page with the redirect link
        query['proxyapproved'] = 'true'
        url_parts[4] = urlencode(query)
        with open(os.path.join(FIXTURE_DIR, 'html_warning_page'), 'r') as f:
            body = f.read().replace('$REDIRECT_URL$', urlunparse(url_parts))
            cookies['proxy_cookie'] = 'foo'
            return MockedResponse(body, 200, cookies)


CHECK_NAME = 'spark'

YARN_CONFIG = {
    'spark_url': 'http://localhost:8088',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_yarn_mode',
    'tags': list(CUSTOM_TAGS),
}

YARN_AUTH_CONFIG = {
    'spark_url': 'http://localhost:8088',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_yarn_mode',
    'tags': list(CUSTOM_TAGS),
    'username': TEST_USERNAME,
    'password': TEST_PASSWORD,
}

MESOS_CONFIG = {
    'spark_url': 'http://localhost:5050',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_mesos_mode',
    'tags': list(CUSTOM_TAGS),
}

MESOS_FILTERED_CONFIG = {
    'spark_url': 'http://localhost:5050',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_mesos_mode',
    'spark_ui_ports': [1234],
}

DRIVER_CONFIG = {
    'spark_url': 'http://localhost:4040',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_driver_mode',
    'tags': list(CUSTOM_TAGS),
}

STANDALONE_CONFIG = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
}

STANDALONE_CONFIG_PRE_20 = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'spark_pre_20_mode': 'true',
}

SSL_CONFIG = {'spark_url': SSL_SERVER_URL, 'cluster_name': CLUSTER_NAME, 'spark_cluster_mode': 'spark_standalone_mode'}

SSL_NO_VERIFY_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'ssl_verify': False,
}

SSL_CERT_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'ssl_verify': os.path.join(CERTIFICATE_DIR, 'cert.cert'),
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

SPARK_JOB_RUNNING_METRIC_TAGS = ['cluster_name:' + CLUSTER_NAME, 'app_name:' + APP_NAME, 'status:running']

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

SPARK_JOB_SUCCEEDED_METRIC_TAGS = ['cluster_name:' + CLUSTER_NAME, 'app_name:' + APP_NAME, 'status:succeeded']

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

SPARK_STAGE_RUNNING_METRIC_TAGS = ['cluster_name:' + CLUSTER_NAME, 'app_name:' + APP_NAME, 'status:running']

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

SPARK_STAGE_COMPLETE_METRIC_TAGS = ['cluster_name:' + CLUSTER_NAME, 'app_name:' + APP_NAME, 'status:complete']

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
}

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

SPARK_METRIC_TAGS = ['cluster_name:' + CLUSTER_NAME, 'app_name:' + APP_NAME]


@pytest.mark.unit
def test_yarn(aggregator):
    with mock.patch('requests.get', yarn_requests_get_mock):
        c = SparkCheck('spark', {}, [YARN_CONFIG])
        c.check(YARN_CONFIG)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        tags = ['url:http://localhost:8088', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
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


@pytest.mark.unit
def test_auth_yarn(aggregator):
    with mock.patch('requests.get', yarn_requests_auth_mock):
        c = SparkCheck('spark', {}, [YARN_AUTH_CONFIG])
        c.check(YARN_AUTH_CONFIG)

        tags = ['url:http://localhost:8088', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
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
def test_mesos(aggregator):
    with mock.patch('requests.get', mesos_requests_get_mock):
        c = SparkCheck('spark', {}, [MESOS_CONFIG])
        c.check(MESOS_CONFIG)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the service tests

        for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            tags = ['url:http://localhost:5050', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
            tags.sort()
            sc.tags.sort()
            assert sc.tags == tags
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            tags = ['url:http://localhost:4040', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
            tags.sort()
            sc.tags.sort()
            assert sc.tags == tags

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_mesos_filter(aggregator):
    with mock.patch('requests.get', mesos_requests_get_mock):
        c = SparkCheck('spark', {}, [MESOS_FILTERED_CONFIG])
        c.check(MESOS_FILTERED_CONFIG)

        for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:5050', 'cluster_name:SparkCluster']

        assert aggregator.metrics_asserted_pct == 100.0


@pytest.mark.unit
def test_driver_unit(aggregator):
    with mock.patch('requests.get', driver_requests_get_mock):
        c = SparkCheck('spark', {}, [DRIVER_CONFIG])
        c.check(DRIVER_CONFIG)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the service tests

        for sc in aggregator.service_checks(SPARK_DRIVER_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            tags = ['url:http://localhost:4040', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
            tags.sort()
            sc.tags.sort()
            assert sc.tags == tags
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            tags = ['url:http://localhost:4040', 'cluster_name:SparkCluster'] + CUSTOM_TAGS
            tags.sort()
            sc.tags.sort()
            assert sc.tags == tags

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_standalone_unit(aggregator):
    with mock.patch('requests.get', standalone_requests_get_mock):
        c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
        c.check(STANDALONE_CONFIG)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the service tests
        for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:8080', 'cluster_name:SparkCluster']
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:4040', 'cluster_name:SparkCluster']

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_standalone_unit_with_proxy_warning_page(aggregator):
    c = SparkCheck('spark', {}, [STANDALONE_CONFIG])
    with mock.patch('requests.get', proxy_with_warning_page_mock):
        c.check(STANDALONE_CONFIG)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the service tests
        for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:8080', 'cluster_name:SparkCluster']
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:4040', 'cluster_name:SparkCluster']

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_standalone_pre20(aggregator):
    with mock.patch('requests.get', standalone_requests_pre20_get_mock):
        c = SparkCheck('spark', {}, [STANDALONE_CONFIG_PRE_20])
        c.check(STANDALONE_CONFIG_PRE_20)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the running job metrics
        for metric, value in iteritems(SPARK_JOB_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in iteritems(SPARK_JOB_SUCCEEDED_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in iteritems(SPARK_STAGE_RUNNING_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in iteritems(SPARK_STAGE_COMPLETE_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in iteritems(SPARK_DRIVER_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in iteritems(SPARK_EXECUTOR_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in iteritems(SPARK_RDD_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the streaming statistics metrics
        for metric, value in iteritems(SPARK_STREAMING_STATISTICS_METRIC_VALUES):
            aggregator.assert_metric(metric, value=value, tags=SPARK_METRIC_TAGS)

        # Check the service tests
        for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:8080', 'cluster_name:SparkCluster']
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:4040', 'cluster_name:SparkCluster']

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_metadata(aggregator, datadog_agent):
    with mock.patch('requests.get', standalone_requests_pre20_get_mock):
        c = SparkCheck(CHECK_NAME, {}, [STANDALONE_CONFIG_PRE_20])
        c.check_id = "test:123"
        c.check(STANDALONE_CONFIG_PRE_20)

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
def test_ssl():
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_CONFIG])

    with pytest.raises(requests.exceptions.SSLError):
        c.check(SSL_CONFIG)


@pytest.mark.unit
def test_ssl_no_verify():
    # Disable ssl warning for self signed cert/no verify
    urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_NO_VERIFY_CONFIG])

    c.check(SSL_NO_VERIFY_CONFIG)


@pytest.mark.unit
def test_ssl_cert():
    # Disable ssl warning for self signed cert/no verify
    urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', {}, [SSL_CERT_CONFIG])

    c.check(SSL_CERT_CONFIG)


@pytest.mark.unit
def test_do_not_crash_on_single_app_failure():
    running_apps = {'foo': ('bar', 'http://foo.bar/'), 'foo2': ('bar', 'http://foo.bar/')}
    results = []
    rest_requests_to_json = mock.MagicMock(side_effect=[RequestException, results])
    c = SparkCheck('spark', {}, [INSTANCE_STANDALONE])

    with mock.patch.object(c, '_rest_request_to_json', rest_requests_to_json), mock.patch.object(c, '_collect_version'):
        c._get_spark_app_ids(running_apps, [])
        assert rest_requests_to_json.call_count == 2


class StandaloneAppsResponseHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'rb') as f:
            self.wfile.write(f.read())


def run_ssl_server():
    cert_file = os.path.join(CERTIFICATE_DIR, 'server.pem')

    httpd = BaseHTTPServer.HTTPServer((SSL_SERVER_ADDRESS, SSL_SERVER_PORT), StandaloneAppsResponseHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile=cert_file, server_side=False)
    httpd.timeout = 5

    threading.Thread(target=httpd.handle_request).start()
    time.sleep(0.5)
    return httpd


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'instance, service_check, cluster_name, spark_url',
    [
        pytest.param(
            INSTANCE_STANDALONE,
            'spark.standalone_master.can_connect',
            'SparkCluster',
            'http://{}:8080'.format(HOST),
            id='standalone',
        ),
        pytest.param(
            INSTANCE_DRIVER, 'spark.driver.can_connect', 'SparkDriver', 'http://{}:4040'.format(HOST), id='driver',
        ),
    ],
)
@pytest.mark.integration
def test_integration(aggregator, instance, service_check, cluster_name, spark_url):
    c = SparkCheck('spark', {}, [instance])
    c.check(instance)

    # Check the running job metrics
    for metric in SPARK_JOB_RUNNING_METRIC_VALUES:
        aggregator.assert_metric(metric)

    # Check the succeeded job metrics
    for metric in SPARK_JOB_SUCCEEDED_METRIC_VALUES:
        aggregator.assert_metric(metric)

    # Check the running stage metrics
    for metric in SPARK_STAGE_RUNNING_METRIC_VALUES:
        aggregator.assert_metric(metric)

    # Check the complete stage metrics
    for metric in SPARK_STAGE_COMPLETE_METRIC_VALUES:
        aggregator.assert_metric(metric)

    # Check the driver metrics
    for metric in SPARK_DRIVER_METRIC_VALUES:
        aggregator.assert_metric(metric)

    # Check the streaming statistics metrics and remove 2 we're not getting for now
    streaming_statistics = set(SPARK_STREAMING_STATISTICS_METRIC_VALUES) - {
        'spark.streaming.statistics.avg_processing_time',
        'spark.streaming.statistics.avg_total_delay',
    }

    for metric in streaming_statistics:
        aggregator.assert_metric(metric)

    # TODO: Further investigate why we aren't getting these, it may be Docker networking
    #
    # # Check the executor metrics
    # for metric in SPARK_EXECUTOR_METRIC_VALUES:
    #     aggregator.assert_metric(metric)
    #
    # # Check the RDD metrics
    # for metric in SPARK_RDD_METRIC_VALUES:
    #     aggregator.assert_metric(metric)

    aggregator.assert_service_check(
        service_check, status=SparkCheck.OK, tags=['cluster_name:{}'.format(cluster_name), 'url:{}'.format(spark_url)],
    )
