# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest
from requests.exceptions import ConnectionError

from datadog_checks.gitlab_runner import GitlabRunnerCheck

from .common import BAD_CONFIG, CONFIG, CUSTOM_TAGS, GITLAB_RUNNER_VERSION, HOST, assert_check

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, dd_run_check):
    instance = CONFIG['instances'][0]
    init_config = copy.deepcopy(CONFIG['init_config'])
    gitlab_runner = GitlabRunnerCheck('gitlab_runner', init_config, instances=[instance])

    dd_run_check(gitlab_runner)
    dd_run_check(gitlab_runner)

    assert_check(aggregator)
    aggregator.assert_all_metrics_covered()


def test_connection_failure(aggregator):
    """
    Make sure we're failing when the URL isn't right
    """

    gitlab_runner = GitlabRunnerCheck('gitlab', BAD_CONFIG['init_config'], instances=BAD_CONFIG['instances'])

    with pytest.raises(ConnectionError):
        gitlab_runner.check(BAD_CONFIG['instances'][0])

    # We should get two failed service checks
    aggregator.assert_service_check(
        GitlabRunnerCheck.MASTER_SERVICE_CHECK_NAME,
        status=GitlabRunnerCheck.CRITICAL,
        tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234'] + CUSTOM_TAGS,
        count=1,
    )

    aggregator.assert_service_check(
        GitlabRunnerCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabRunnerCheck.CRITICAL, tags=CUSTOM_TAGS, count=1
    )


def test_version_metadata(aggregator, datadog_agent, dd_run_check):
    check_instance = GitlabRunnerCheck('gitlab_runner', CONFIG['init_config'], instances=[CONFIG['instances'][0]])
    check_instance.check_id = 'test:123'
    dd_run_check(check_instance)

    raw_version = GITLAB_RUNNER_VERSION

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
