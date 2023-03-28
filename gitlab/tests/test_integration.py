# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError

from datadog_checks.gitlab import GitlabCheck

from .common import AUTH_CONFIG, BAD_CONFIG, CUSTOM_TAGS, HOST

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


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
