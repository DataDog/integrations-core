# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab import GitlabCheck

from .common import (
    ALLOWED_METRICS,
    AUTH_CONFIG,
    CONFIG,
    CUSTOM_TAGS,
    GITLAB_TAGS,
    LEGACY_CONFIG,
    METRICS,
    METRICS_TO_TEST,
)


def assert_check(aggregator, metrics):
    """
    Basic Test for gitlab integration.
    """
    # Make sure we're receiving gitlab service checks
    for service_check in GitlabCheck.ALLOWED_SERVICE_CHECKS:
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check), status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS
        )

    # Make sure we're receiving prometheus service checks
    aggregator.assert_service_check(
        GitlabCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS
    )

    for metric in metrics:
        aggregator.assert_metric("gitlab.{}".format(metric))


@pytest.mark.parametrize(
    'raw_version, version_metadata, count',
    [
        pytest.param(
            '12.7.6',
            {
                'version.scheme': 'semver',
                'version.major': '12',
                'version.minor': '7',
                'version.patch': '6',
                'version.raw': '12.7.6',
            },
            5,
        ),
        pytest.param(
            '1.4.5',
            {
                'version.scheme': 'semver',
                'version.major': '1',
                'version.minor': '4',
                'version.patch': '5',
                'version.raw': '1.4.5',
            },
            5,
        ),
    ],
)
@pytest.mark.usefixtures("dd_environment")
def test_check_submit_metadata(aggregator, datadog_agent, raw_version, version_metadata, count):
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        # mock the api call so that it returns the given version
        g.return_value = {"version": raw_version}

        datadog_agent.reset()

        instance = AUTH_CONFIG['instances'][0]
        init_config = AUTH_CONFIG['init_config']

        gitlab = GitlabCheck('gitlab', init_config, instances=[instance])
        gitlab.check_id = 'test:123'

        gitlab.check(instance)
        datadog_agent.assert_metadata('test:123', version_metadata)
        datadog_agent.assert_metadata_count(count)


@pytest.mark.usefixtures("dd_environment")
def test_check_integration(aggregator, mock_data):
    instance = CONFIG['instances'][0]
    init_config = CONFIG['init_config']

    gitlab = GitlabCheck('gitlab', init_config, instances=[instance])
    gitlab.check(instance)
    gitlab.check(instance)

    assert_check(aggregator, METRICS)


@pytest.mark.e2e
def test_e2e_legacy(dd_agent_check):
    aggregator = dd_agent_check(LEGACY_CONFIG, rate=True)
    assert_check(aggregator, ALLOWED_METRICS)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG, rate=True)
    assert_check(aggregator, METRICS_TO_TEST)
    # Excluding gitlab.rack.http_requests_total because it is a distribution metric
    # (its sum and count metrics are in the metadata)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=["gitlab.rack.http_requests_total"])
