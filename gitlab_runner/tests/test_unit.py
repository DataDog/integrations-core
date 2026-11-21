# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
)
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab_runner import GitlabRunnerCheck

from . import common


@pytest.mark.unit
@pytest.mark.parametrize(
    'test_case, timeout_config, expected_timeout',
    [
        ("legacy config", {"connect_timeout": 8, "receive_timeout": 7}, (8, 7)),
        ("new config", {"connect_timeout": 8, "read_timeout": 7}, (8, 7)),
        ("default timeout", {}, (5, 15)),
    ],
)
def test_timeout(test_case, timeout_config, expected_timeout):
    config = deepcopy(common.CONFIG)

    config['instances'][0].update(timeout_config)

    gitlab_runner = GitlabRunnerCheck('gitlab_runner', common.CONFIG['init_config'], instances=config['instances'])

    # The connectivity check to the GitLab master sends its request through `self.http`.
    assert gitlab_runner.http.options['timeout'] == expected_timeout


@pytest.mark.unit
def test_job_queue_duration_metric(aggregator, dd_run_check, mock_data):
    """
    Test that the gitlab_runner_job_queue_duration_seconds histogram metric
    is automatically collected via METRICS_LIST without user configuration.
    """
    config = deepcopy(common.CONFIG)

    check = GitlabRunnerCheck('gitlab_runner', config['init_config'], instances=config['instances'])
    dd_run_check(check)
    dd_run_check(check)

    expected_tags = ['runner:test-runner'] + common.CUSTOM_TAGS

    # Histogram buckets (reported as .count with upper_bound tags)
    aggregator.assert_metric(
        'gitlab_runner.gitlab_runner_job_queue_duration_seconds.count',
        tags=expected_tags + ['upper_bound:none'],
    )
    # Histogram sum
    aggregator.assert_metric('gitlab_runner.gitlab_runner_job_queue_duration_seconds.sum', tags=expected_tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
@pytest.mark.parametrize(
    'error',
    [
        pytest.param(HTTPClientConnectionError('connection refused'), id='connection'),
        pytest.param(HTTPClientConnectTimeoutError('connect timed out'), id='connect-timeout'),
        pytest.param(HTTPClientReadTimeoutError('read timed out'), id='read-timeout'),
    ],
)
def test_scrape_failure_reports_critical(aggregator, dd_run_check, mock_data, fake_http, error):
    fake_http.register_response('GET', common.GITLAB_RUNNER_URL, error)
    check = GitlabRunnerCheck('gitlab_runner', common.CONFIG['init_config'], instances=common.CONFIG['instances'])

    dd_run_check(check)

    aggregator.assert_service_check(GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.CRITICAL)
