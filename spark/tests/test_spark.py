# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

from urlparse import urlparse, parse_qsl
from urllib import unquote_plus
from urlparse import urljoin
import json
import BaseHTTPServer
import threading
import ssl
import time
import requests
import mock
import pytest

from datadog_checks.stubs import aggregator as _aggregator
from datadog_checks.spark import SparkCheck

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

# Service Check Names
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
MESOS_SERVICE_CHECK = 'spark.mesos_master.can_connect'
STANDALONE_SERVICE_CHECK = 'spark.standalone_master.can_connect'

TEST_USERNAME = 'admin'
TEST_PASSWORD = 'password'

CUSTOM_TAGS = ['optional:tag1']


def join_url_dir(url, *args):
    '''
    Join a URL with multiple directories
    '''
    for path in args:
        url = url.rstrip('/') + '/'
        url = urljoin(url, path.lstrip('/'))

    return url


class Url(object):
    '''A url object that can be compared with other url orbjects
    without regard to the vagaries of encoding, escaping, and ordering
    of parameters in query strings.'''

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


# YARN Service URLs
YARN_APP_URL = Url(urljoin(SPARK_YARN_URL, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=SPARK')
YARN_SPARK_APP_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH))
YARN_SPARK_JOB_URL = Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
YARN_SPARK_STAGE_URL = \
    Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
YARN_SPARK_EXECUTOR_URL = \
    Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
YARN_SPARK_RDD_URL = \
    Url(join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))

# Mesos Service URLs
MESOS_APP_URL = Url(urljoin(SPARK_MESOS_URL, MESOS_APPS_PATH))
MESOS_SPARK_APP_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH))
MESOS_SPARK_JOB_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
MESOS_SPARK_STAGE_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
MESOS_SPARK_EXECUTOR_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
MESOS_SPARK_RDD_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))

# Spark Standalone Service URLs
STANDALONE_APP_URL = Url(urljoin(STANDALONE_URL, STANDALONE_APPS_PATH))
STANDALONE_APP_HTML_URL = Url(urljoin(STANDALONE_URL, STANDALONE_APP_PATH_HTML) + '?appId=' + SPARK_APP_ID)
STANDALONE_SPARK_APP_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH))
STANDALONE_SPARK_JOB_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs'))
STANDALONE_SPARK_STAGE_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages'))
STANDALONE_SPARK_EXECUTOR_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors'))
STANDALONE_SPARK_RDD_URL = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd'))

STANDALONE_SPARK_JOB_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'jobs'))
STANDALONE_SPARK_STAGE_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'stages'))
STANDALONE_SPARK_EXECUTOR_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'executors'))
STANDALONE_SPARK_RDD_URL_PRE20 = Url(join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, APP_NAME, 'storage/rdd'))

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')


@pytest.fixture
def aggregator():
    _aggregator.reset()
    return _aggregator


def yarn_requests_get_mock(*args, **kwargs):

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    arg_url = Url(args[0])

    if arg_url == YARN_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'yarn_apps'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif arg_url == YARN_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif arg_url == YARN_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif arg_url == YARN_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif arg_url == YARN_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif arg_url == YARN_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)


def yarn_requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return yarn_requests_get_mock(*args, **kwargs)


def mesos_requests_get_mock(*args, **kwargs):

    class MockMesosResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    arg_url = Url(args[0])

    if arg_url == MESOS_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'mesos_apps'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif arg_url == MESOS_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif arg_url == MESOS_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif arg_url == MESOS_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif arg_url == MESOS_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif arg_url == MESOS_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)


def standalone_requests_get_mock(*args, **kwargs):

    class MockStandaloneResponse:
        text = ''

        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json_data

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    arg_url = Url(args[0])

    if arg_url == STANDALONE_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_APP_HTML_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_app'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_JOB_URL:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_RDD_URL:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)


def standalone_requests_pre20_get_mock(*args, **kwargs):

    class MockStandaloneResponse:
        text = ''

        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json_data

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    arg_url = Url(args[0])

    if arg_url == STANDALONE_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_APP_HTML_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_app'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_APP_URL:
        with open(os.path.join(FIXTURE_DIR, 'spark_apps_pre20'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_JOB_URL:
        return MockStandaloneResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_STAGE_URL:
        return MockStandaloneResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL:
        return MockStandaloneResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_RDD_URL:
        return MockStandaloneResponse("{}", 404)

    elif arg_url == STANDALONE_SPARK_JOB_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'job_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_STAGE_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'stage_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_EXECUTOR_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'executor_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif arg_url == STANDALONE_SPARK_RDD_URL_PRE20:
        with open(os.path.join(FIXTURE_DIR, 'rdd_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)


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
    'spark_ui_ports': [1234]
}

STANDALONE_CONFIG = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode'
}
STANDALONE_CONFIG_PRE_20 = {
    'spark_url': 'http://localhost:8080',
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'spark_pre_20_mode': 'true'
}

SSL_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode'
}

SSL_NO_VERIFY_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'ssl_verify': False
}

SSL_CERT_CONFIG = {
    'spark_url': SSL_SERVER_URL,
    'cluster_name': CLUSTER_NAME,
    'spark_cluster_mode': 'spark_standalone_mode',
    'ssl_verify': os.path.join(CERTIFICATE_DIR, 'cert.cert')
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
    'spark.job.num_failed_stages': 100
}

SPARK_JOB_RUNNING_METRIC_TAGS = [
    'cluster_name:' + CLUSTER_NAME,
    'app_name:' + APP_NAME,
    'status:running',
]

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
    'spark.job.num_failed_stages': 9000
}

SPARK_JOB_SUCCEEDED_METRIC_TAGS = [
    'cluster_name:' + CLUSTER_NAME,
    'app_name:' + APP_NAME,
    'status:succeeded',
]

SPARK_STAGE_RUNNING_METRIC_VALUES = {
    'spark.stage.count': 3,
    'spark.stage.num_active_tasks': 3*3,
    'spark.stage.num_complete_tasks': 4*3,
    'spark.stage.num_failed_tasks': 5*3,
    'spark.stage.executor_run_time': 6*3,
    'spark.stage.input_bytes': 7*3,
    'spark.stage.input_records': 8*3,
    'spark.stage.output_bytes': 9*3,
    'spark.stage.output_records': 10*3,
    'spark.stage.shuffle_read_bytes': 11*3,
    'spark.stage.shuffle_read_records': 12*3,
    'spark.stage.shuffle_write_bytes': 13*3,
    'spark.stage.shuffle_write_records': 14*3,
    'spark.stage.memory_bytes_spilled': 15*3,
    'spark.stage.disk_bytes_spilled': 16*3,
}

SPARK_STAGE_RUNNING_METRIC_TAGS = [
    'cluster_name:' + CLUSTER_NAME,
    'app_name:' + APP_NAME,
    'status:running',
]

SPARK_STAGE_COMPLETE_METRIC_VALUES = {
    'spark.stage.count': 2,
    'spark.stage.num_active_tasks': 100*2,
    'spark.stage.num_complete_tasks': 101*2,
    'spark.stage.num_failed_tasks': 102*2,
    'spark.stage.executor_run_time': 103*2,
    'spark.stage.input_bytes': 104*2,
    'spark.stage.input_records': 105*2,
    'spark.stage.output_bytes': 106*2,
    'spark.stage.output_records': 107*2,
    'spark.stage.shuffle_read_bytes': 108*2,
    'spark.stage.shuffle_read_records': 109*2,
    'spark.stage.shuffle_write_bytes': 110*2,
    'spark.stage.shuffle_write_records': 111*2,
    'spark.stage.memory_bytes_spilled': 112*2,
    'spark.stage.disk_bytes_spilled': 113*2,
}

SPARK_STAGE_COMPLETE_METRIC_TAGS = [
    'cluster_name:' + CLUSTER_NAME,
    'app_name:' + APP_NAME,
    'status:complete',
]

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

SPARK_METRIC_TAGS = [
    'cluster_name:' + CLUSTER_NAME,
    'app_name:' + APP_NAME
]


def test_yarn(aggregator):
    with mock.patch('requests.get', yarn_requests_get_mock):
        c = SparkCheck('spark', None, {}, [YARN_CONFIG])
        c.check(YARN_CONFIG)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS, value=value)

        # Check the succeeded job metrics
        for metric, value in SPARK_JOB_SUCCEEDED_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS)

        # Check the running stage metrics
        for metric, value in SPARK_STAGE_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the complete stage metrics
        for metric, value in SPARK_STAGE_COMPLETE_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS)

        # Check the driver metrics
        for metric, value in SPARK_DRIVER_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the executor metrics
        for metric, value in SPARK_EXECUTOR_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the RDD metrics
        for metric, value in SPARK_RDD_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

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


def test_auth_yarn(aggregator):
    with mock.patch('requests.get', yarn_requests_auth_mock):
        c = SparkCheck('spark', None, {}, [YARN_AUTH_CONFIG])
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


def test_mesos(aggregator):
    with mock.patch('requests.get', mesos_requests_get_mock):
        c = SparkCheck('spark', None, {}, [MESOS_CONFIG])
        c.check(MESOS_CONFIG)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the succeeded job metrics
        for metric, value in SPARK_JOB_SUCCEEDED_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS + CUSTOM_TAGS)

        # Check the running stage metrics
        for metric, value in SPARK_STAGE_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_RUNNING_METRIC_TAGS + CUSTOM_TAGS)

        # Check the complete stage metrics
        for metric, value in SPARK_STAGE_COMPLETE_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_COMPLETE_METRIC_TAGS + CUSTOM_TAGS)

        # Check the driver metrics
        for metric, value in SPARK_DRIVER_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the executor metrics
        for metric, value in SPARK_EXECUTOR_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

        # Check the RDD metrics
        for metric, value in SPARK_RDD_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS + CUSTOM_TAGS)

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

        assert aggregator.metrics_asserted_pct == 100.0


def test_mesos_filter(aggregator):
    with mock.patch('requests.get', mesos_requests_get_mock):
        c = SparkCheck('spark', None, {}, [MESOS_FILTERED_CONFIG])
        c.check(MESOS_FILTERED_CONFIG)

        for sc in aggregator.service_checks(MESOS_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:5050', 'cluster_name:SparkCluster']

        assert aggregator.metrics_asserted_pct == 100.0


def test_standalone(aggregator):
    with mock.patch('requests.get', standalone_requests_get_mock):
        c = SparkCheck('spark', None, {}, [STANDALONE_CONFIG])
        c.check(STANDALONE_CONFIG)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in SPARK_JOB_SUCCEEDED_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in SPARK_STAGE_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in SPARK_STAGE_COMPLETE_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in SPARK_DRIVER_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in SPARK_EXECUTOR_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in SPARK_RDD_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the service tests
        for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:8080', 'cluster_name:SparkCluster']
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:4040', 'cluster_name:SparkCluster']


def test_standalone_pre20(aggregator):
    with mock.patch('requests.get', standalone_requests_pre20_get_mock):
        c = SparkCheck('spark', None, {}, [STANDALONE_CONFIG_PRE_20])
        c.check(STANDALONE_CONFIG_PRE_20)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the running job metrics
        for metric, value in SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in SPARK_JOB_SUCCEEDED_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in SPARK_STAGE_RUNNING_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in SPARK_STAGE_COMPLETE_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in SPARK_DRIVER_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in SPARK_EXECUTOR_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in SPARK_RDD_METRIC_VALUES.iteritems():
            aggregator.assert_metric(
                metric,
                value=value,
                tags=SPARK_METRIC_TAGS)

        # Check the service tests
        for sc in aggregator.service_checks(STANDALONE_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:8080', 'cluster_name:SparkCluster']
        for sc in aggregator.service_checks(SPARK_SERVICE_CHECK):
            assert sc.status == SparkCheck.OK
            assert sc.tags == ['url:http://localhost:4040', 'cluster_name:SparkCluster']


def test_ssl():
    run_ssl_server()
    c = SparkCheck('spark', None, {}, [SSL_CONFIG])

    with pytest.raises(requests.exceptions.SSLError):
        c.check(SSL_CONFIG)


def test_ssl_no_verify():
    # Disable ssl warning for self signed cert/no verify
    requests.packages.urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', None, {}, [SSL_NO_VERIFY_CONFIG])

    c.check(SSL_NO_VERIFY_CONFIG)


def test_ssl_cert():
    # Disable ssl warning for self signed cert/no verify
    requests.packages.urllib3.disable_warnings()
    run_ssl_server()
    c = SparkCheck('spark', None, {}, [SSL_CERT_CONFIG])

    c.check(SSL_CERT_CONFIG)


class StandaloneAppsResponseHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        with open(os.path.join(FIXTURE_DIR, 'spark_standalone_apps'), 'r') as f:
            self.wfile.write(f.read())


def run_ssl_server():
    cert_file = os.path.join(CERTIFICATE_DIR, 'server.pem')

    httpd = BaseHTTPServer.HTTPServer((SSL_SERVER_ADDRESS, SSL_SERVER_PORT), StandaloneAppsResponseHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile=cert_file, server_side=False)
    httpd.timeout = 5

    threading.Thread(target=httpd.handle_request).start()
    time.sleep(.5)
    return httpd
