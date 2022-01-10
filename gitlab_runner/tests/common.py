# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab_runner import GitlabRunnerCheck

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()

GITLAB_TEST_TOKEN = "ddtesttoken"
GITLAB_LOCAL_MASTER_PORT = 8085
GITLAB_LOCAL_RUNNER_PORT = 8087

GITLAB_MASTER_URL = "http://{}:{}".format(HOST, GITLAB_LOCAL_MASTER_PORT)
GITLAB_RUNNER_URL = "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_RUNNER_PORT)

GITLAB_RUNNER_TAGS = ['gitlab_host:{}'.format(HOST), 'gitlab_port:{}'.format(GITLAB_LOCAL_MASTER_PORT)]

GITLAB_RUNNER_VERSION = os.environ['GITLAB_RUNNER_VERSION']

CUSTOM_TAGS = ['optional:tag1']

# Note that this is a subset of the ones defined in GitlabCheck
# When we stand up a clean test infrastructure some of those metrics might not
# be available yet, hence we validate a stable subset
ALLOWED_METRICS = [
    'ci_runner_errors',
    'ci_runner_version_info',
    'process_max_fds',
    'process_open_fds',
    'process_resident_memory_bytes',
    'process_start_time_seconds',
    'process_virtual_memory_bytes',
]

CONFIG = {
    'init_config': {'allowed_metrics': ALLOWED_METRICS},
    'instances': [
        {
            'prometheus_endpoint': GITLAB_RUNNER_URL,
            'gitlab_url': '{}/ci'.format(GITLAB_MASTER_URL),
            'send_monotonic_counter': True,
            'disable_ssl_validation': True,
            'tags': list(CUSTOM_TAGS),
        }
    ],
    'logs': [
        {
            "type": "docker",
            "source": "gitlab-runner",
        }
    ],
}

BAD_CONFIG = {
    'init_config': {'allowed_metrics': ALLOWED_METRICS},
    'instances': [
        {
            'prometheus_endpoint': 'http://{}:1234/metrics'.format(HOST),
            'gitlab_url': 'http://{}:1234/ci'.format(HOST),
            'disable_ssl_validation': True,
            'tags': list(CUSTOM_TAGS),
        }
    ],
}


def assert_check(aggregator):
    """
    Basic Test for gitlab integration.
    """
    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.OK,
        tags=GITLAB_RUNNER_TAGS + CUSTOM_TAGS,
        count=2,
    )
    aggregator.assert_service_check(
        GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.OK, tags=CUSTOM_TAGS, count=2
    )
    for metric in ALLOWED_METRICS:
        metric_name = "gitlab_runner.{}".format(metric)
        if metric.startswith('ci_runner'):
            aggregator.assert_metric(metric_name)
        else:
            aggregator.assert_metric(metric_name, tags=CUSTOM_TAGS, count=2)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
