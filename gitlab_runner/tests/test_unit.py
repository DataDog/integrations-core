# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import mock
import pytest

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

    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200)

        gitlab_runner.check(config['instances'][0])

        r.get.assert_called_with(
            'http://localhost:8085/ci',
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=expected_timeout,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )


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
