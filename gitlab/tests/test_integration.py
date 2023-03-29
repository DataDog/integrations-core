# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError

from datadog_checks.gitlab import GitlabCheck

from .common import CUSTOM_TAGS, HOST, METRICS_TO_TEST, assert_check

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


def test_check(dd_run_check, aggregator, gitlab_check, config):
    """
    Make sure we're failing when the URL isn't right
    """
    check = gitlab_check(config)
    dd_run_check(check)

    assert_check(aggregator, METRICS_TO_TEST)


def test_connection_failure(aggregator, gitlab_check, bad_config):
    """
    Make sure we're failing when the URL isn't right
    """

    check = gitlab_check(bad_config)

    with pytest.raises(ConnectionError):
        check.check(None)

    aggregator.assert_service_check(
        'gitlab.prometheus_endpoint_up',
        status=GitlabCheck.CRITICAL,
        count=1,
    )

    # We should get only one extra failed service check, the first (readiness)
    aggregator.assert_service_check(
        'gitlab.readiness',
        status=GitlabCheck.CRITICAL,
        tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234'] + CUSTOM_TAGS,
        count=1,
    )

    for service_check in ('liveness', 'health'):
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check),
            count=0,
        )


@pytest.mark.parametrize(
    'raw_version, version_metadata',
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
        ),
    ],
)
@pytest.mark.parametrize('enable_metadata_collection', [True, False])
def test_check_submit_metadata(
    dd_run_check,
    aggregator,
    datadog_agent,
    raw_version,
    version_metadata,
    gitlab_check,
    auth_config,
    enable_metadata_collection,
):
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        # mock the api call so that it returns the given version
        g.return_value = {"version": raw_version}

        datadog_agent.reset()
        datadog_agent._config["enable_metadata_collection"] = enable_metadata_collection

        dd_run_check(gitlab_check(auth_config))

        if enable_metadata_collection:
            g.assert_called_once()
            datadog_agent.assert_metadata('test:123', version_metadata)
            datadog_agent.assert_metadata_count(5)
        else:
            g.assert_not_called()
            datadog_agent.assert_metadata_count(0)
