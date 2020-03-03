# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.gitlab import GitlabCheck

from .common import ALLOWED_METRICS, AUTH_CONFIG, CONFIG, CUSTOM_TAGS, GITLAB_TAGS


def assert_check(aggregator):
    """
    Basic Test for gitlab integration.
    """
    # Make sure we're receiving gitlab service checks
    for service_check in GitlabCheck.ALLOWED_SERVICE_CHECKS:
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check), status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS, count=2
        )

    # Make sure we're receiving prometheus service checks
    aggregator.assert_service_check(
        GitlabCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabCheck.OK, tags=CUSTOM_TAGS, count=2
    )

    for metric in ALLOWED_METRICS:
        aggregator.assert_metric("gitlab.{}".format(metric), tags=CUSTOM_TAGS, count=2)


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
        with mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled') as m:
            # mock the api call so that it returns the given version
            g.return_value = {"version": raw_version}
            m.return_value = True

            instance = AUTH_CONFIG['instances'][0]
            init_config = AUTH_CONFIG['init_config']

            gitlab = GitlabCheck('gitlab', init_config, instances=[instance])
            gitlab.check_id = 'test:123'

            gitlab.check(instance)
            datadog_agent.assert_metadata('test:123', version_metadata)
            datadog_agent.assert_metadata_count(count)


@pytest.mark.usefixtures("dd_environment")
def test_check_integration(aggregator):
    instance = CONFIG['instances'][0]
    init_config = CONFIG['init_config']

    gitlab = GitlabCheck('gitlab', init_config, instances=[instance])

    gitlab.check(instance)
    gitlab.check(instance)

    assert_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG, rate=True)

    assert_check(aggregator)
