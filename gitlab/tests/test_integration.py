# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from requests.exceptions import ConnectionError

from datadog_checks.gitlab import GitlabCheck

from .common import BAD_CONFIG, CUSTOM_TAGS, HOST


@pytest.mark.usefixtures("dd_environment")
def test_connection_failure(aggregator):
    """
    Make sure we're failing when the URL isn't right
    """

    gitlab = GitlabCheck('gitlab', BAD_CONFIG['init_config'], instances=BAD_CONFIG['instances'])

    with pytest.raises(ConnectionError):
        gitlab.check(BAD_CONFIG['instances'][0])

    # We should get only one failed service check, the first
    aggregator.assert_service_check(
        'gitlab.{}'.format(GitlabCheck.ALLOWED_SERVICE_CHECKS[0]),
        status=GitlabCheck.CRITICAL,
        tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234'] + CUSTOM_TAGS,
        count=1,
    )
