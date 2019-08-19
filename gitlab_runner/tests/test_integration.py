# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from requests.exceptions import ConnectionError

from datadog_checks.gitlab_runner import GitlabRunnerCheck

from .common import BAD_CONFIG, CUSTOM_TAGS, HOST


@pytest.mark.usefixtures("dd_environment")
def test_connection_failure(aggregator):
    """
    Make sure we're failing when the URL isn't right
    """

    gitlab_runner = GitlabRunnerCheck('gitlab', BAD_CONFIG['init_config'], {}, instances=BAD_CONFIG['instances'])

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
