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

    # Assert hardcoded default metrics and their histogram/summary sub-metrics
    default_metrics = [
        'ci_docker_machines_provider_machine_creation_duration_seconds',
        'ci_docker_machines_provider_machine_states',
        'ci_runner_builds',
        'ci_runner_errors',
        'ci_ssh_docker_machines_provider_machine_creation_duration_seconds',
        'ci_ssh_docker_machines_provider_machine_states',
        'gitlab_runner_api_request_duration_seconds',
        'gitlab_runner_autoscaling_machine_creation_duration_seconds',
        'gitlab_runner_autoscaling_machine_states',
        'gitlab_runner_errors_total',
        'gitlab_runner_job_queue_duration_seconds',
        'gitlab_runner_jobs',
        'gitlab_runner_version_info',
        'go_gc_duration_seconds',
        'go_goroutines',
        'go_memstats_alloc_bytes',
        'go_memstats_alloc_bytes_total',
        'go_memstats_buck_hash_sys_bytes',
        'go_memstats_frees_total',
        'go_memstats_gc_sys_bytes',
        'go_memstats_heap_alloc_bytes',
        'go_memstats_heap_idle_bytes',
        'go_memstats_heap_inuse_bytes',
        'go_memstats_heap_objects',
        'go_memstats_heap_released_bytes_total',
        'go_memstats_heap_sys_bytes',
        'go_memstats_last_gc_time_seconds',
        'go_memstats_lookups_total',
        'go_memstats_mallocs_total',
        'go_memstats_mcache_inuse_bytes',
        'go_memstats_mcache_sys_bytes',
        'go_memstats_mspan_inuse_bytes',
        'go_memstats_mspan_sys_bytes',
        'go_memstats_next_gc_bytes',
        'go_memstats_other_sys_bytes',
        'go_memstats_stack_inuse_bytes',
        'go_memstats_stack_sys_bytes',
        'go_memstats_sys_bytes',
        'process_cpu_seconds_total',
        'process_max_fds',
        'process_open_fds',
        'process_resident_memory_bytes',
        'process_start_time_seconds',
        'process_virtual_memory_bytes',
    ]
    for metric in default_metrics:
        metric_name = "gitlab_runner.{}".format(metric)
        aggregator.assert_metric(metric_name, at_least=0, tags=CUSTOM_TAGS)
        for suffix in ('.count', '.sum', '.quantile', '.bucket'):
            aggregator.assert_metric(metric_name + suffix, at_least=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
