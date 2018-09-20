# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.gitlab import GitlabCheck
from .common import HOST, CONFIG, BAD_CONFIG, GITLAB_TAGS, CUSTOM_TAGS, ALLOWED_METRICS

import pytest
from requests.exceptions import ConnectionError


def test_check(aggregator):
    """
    Basic Test for gitlab integration.
    """

    gitlab = GitlabCheck('gitlab', CONFIG['init_config'], {}, instances=CONFIG['instances'])

    gitlab.check(CONFIG['instances'][0])

    # Make sure we're receiving gitlab service checks
    for service_check in GitlabCheck.ALLOWED_SERVICE_CHECKS:
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check), status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS, count=1
        )

    # Make sure we're receiving prometheus service checks
    aggregator.assert_service_check(
        GitlabCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabCheck.OK, tags=CUSTOM_TAGS, count=1
    )

    for metric in ALLOWED_METRICS:
        aggregator.assert_metric("gitlab.{}".format(metric), tags=CUSTOM_TAGS, count=1)


def test_connection_failure(aggregator):
    """
    Make sure we're failing when the URL isn't right
    """

    gitlab = GitlabCheck('gitlab', BAD_CONFIG['init_config'], {}, instances=BAD_CONFIG['instances'])

    with pytest.raises(ConnectionError):
        gitlab.check(BAD_CONFIG['instances'][0])

    # We should get only one failed service check, the first
    aggregator.assert_service_check(
        'gitlab.{}'.format(GitlabCheck.ALLOWED_SERVICE_CHECKS[0]),
        status=GitlabCheck.CRITICAL,
        tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234'] + CUSTOM_TAGS,
        count=1
    )
