# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from flaky import flaky

from datadog_checks.gitlab_runner import GitlabRunnerCheck

from .common import CONFIG, CUSTOM_TAGS, GITLAB_RUNNER_TAGS


def _rerun_on_502_response(err, name, test, plugin):
    """
    Gitlab randomly returns 502 sometimes even if it's up and running fine.

    In this case we just want to retry the request without waiting.
    """

    we_retry = 'Http status code 502 on url' in str(err)
    if we_retry:
        time.sleep(5)
    return we_retry


@flaky(max_runs=5, rerun_filter=_rerun_on_502_response)
def test_e2e(dd_agent_check):
    """
    Because this test's flakiness is very specific we still run it in master CI.

    We retry it to get past the transient 502 response.
    """

    aggregator = dd_agent_check(CONFIG)
    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.OK, tags=GITLAB_RUNNER_TAGS + CUSTOM_TAGS
    )
    aggregator.assert_service_check(
        GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.OK, tags=CUSTOM_TAGS
    )
