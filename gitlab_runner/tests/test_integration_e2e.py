# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab_runner import GitlabRunnerCheck

from .common import ALLOWED_METRICS, CONFIG, CUSTOM_TAGS, GITLAB_RUNNER_TAGS


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
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, dd_run_check):
    instance = CONFIG['instances'][0]
    init_config = copy.deepcopy(CONFIG['init_config'])
    gitlab_runner = GitlabRunnerCheck('gitlab_runner', init_config, instances=[instance])

    dd_run_check(gitlab_runner)
    dd_run_check(gitlab_runner)

    assert_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG, rate=True)

    assert_check(aggregator)
