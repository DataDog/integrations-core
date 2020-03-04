# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.gitlab import GitlabCheck

from .common import ALLOWED_METRICS, CONFIG, CUSTOM_TAGS, GITLAB_TAGS, LEGACY_CONFIG, METRICS


def assert_check(aggregator):
    """
    Basic Test for gitlab integration.
    """
    # Make sure we're receiving gitlab service checks
    for service_check in GitlabCheck.ALLOWED_SERVICE_CHECKS:
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check), status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS
        )

    # Make sure we're receiving prometheus service checks
    aggregator.assert_service_check(GitlabCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabCheck.OK, tags=CUSTOM_TAGS)

    for metric in METRICS:
        aggregator.assert_metric("gitlab.{}".format(metric))


@pytest.mark.usefixtures("dd_environment")
def test_check_integration(aggregator, mock_data):
    instance = CONFIG['instances'][0]
    init_config = CONFIG['init_config']

    gitlab = GitlabCheck('gitlab', init_config, instances=[instance])
    gitlab.check(instance)

    assert_check(aggregator)
    for metric in METRICS:
        aggregator.assert_metric("gitlab.{}".format(metric))


@pytest.mark.e2e
def test_e2e_legacy(dd_agent_check):
    aggregator = dd_agent_check(LEGACY_CONFIG, rate=True)
    for metric in ALLOWED_METRICS:
        aggregator.assert_metric("gitlab.{}".format(metric), tags=CUSTOM_TAGS, count=2)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    assert_check(aggregator)
