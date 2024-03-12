# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.gitlab_runner import GitlabRunnerCheck

from .common import CONFIG, CUSTOM_TAGS, GITLAB_RUNNER_TAGS


def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.OK, tags=GITLAB_RUNNER_TAGS + CUSTOM_TAGS
    )
    aggregator.assert_service_check(
        GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.OK, tags=CUSTOM_TAGS
    )
