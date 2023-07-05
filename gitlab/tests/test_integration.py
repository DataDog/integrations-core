# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError

from datadog_checks.dev.testing import requires_py3
from datadog_checks.gitlab import GitlabCheck

from .common import (
    CUSTOM_TAGS,
    GITALY_METRICS_TO_TEST,
    GITLAB_GITALY_PROMETHEUS_ENDPOINT,
    GITLAB_TAGS,
    HOST,
    METRICS_TO_TEST,
    METRICS_TO_TEST_V2,
    assert_check,
)

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_check(dd_run_check, aggregator, gitlab_check, get_config, use_openmetrics):
    check = gitlab_check(get_config(use_openmetrics))
    dd_run_check(check)

    assert_check(aggregator, METRICS_TO_TEST_V2 if use_openmetrics else METRICS_TO_TEST, use_openmetrics)


@requires_py3
def test_check_gitaly(dd_run_check, aggregator, gitlab_check, get_config):
    from datadog_checks.gitlab.gitlab_v2 import GitlabCheckV2

    config = get_config(True)
    instance = config['instances'][0]
    instance["gitaly_server_endpoint"] = GITLAB_GITALY_PROMETHEUS_ENDPOINT

    dd_run_check(gitlab_check(config))

    assert_check(aggregator, METRICS_TO_TEST_V2 + GITALY_METRICS_TO_TEST, True)
    aggregator.assert_service_check(
        'gitlab.gitaly.openmetrics.health',
        status=GitlabCheckV2.OK,
        tags=GITLAB_TAGS + CUSTOM_TAGS + ['endpoint:{}'.format(GITLAB_GITALY_PROMETHEUS_ENDPOINT)],
    )


def test_connection_failure(aggregator, gitlab_check, get_bad_config):
    check = gitlab_check(get_bad_config(False))

    with pytest.raises(ConnectionError):
        check.check(None)

    # We should get only one extra failed service check, the first (readiness)
    for service_check in ("prometheus_endpoint_up", "readiness"):
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check),
            status=GitlabCheck.CRITICAL,
            tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234'] + CUSTOM_TAGS,
            count=1,
        )

    for service_check in ('liveness', 'health'):
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check),
            count=0,
        )


@requires_py3
def test_connection_failure_openmetrics(dd_run_check, aggregator, gitlab_check, get_bad_config):
    check = gitlab_check(get_bad_config(True))

    with pytest.raises(Exception, match="requests.exceptions.ConnectionError"):
        dd_run_check(check)

    aggregator.assert_service_check(
        'gitlab.openmetrics.health',
        status=GitlabCheck.CRITICAL,
        tags=['gitlab_host:{}'.format(HOST), 'gitlab_port:1234']
        + CUSTOM_TAGS
        + ['endpoint:http://localhost:1234/-/metrics'],
        count=1,
    )

    for service_check in ('readiness', 'liveness', 'health'):
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check),
            status=GitlabCheck.CRITICAL,
            count=1,
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
            id="12.7.9",
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
            id="1.4.5",
        ),
    ],
)
@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
@pytest.mark.parametrize('enable_metadata_collection', [True, False])
def test_check_submit_metadata(
    dd_run_check,
    aggregator,
    datadog_agent,
    raw_version,
    version_metadata,
    gitlab_check,
    get_auth_config,
    enable_metadata_collection,
    use_openmetrics,
):
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        # mock the api call so that it returns the given version
        g.return_value = {"version": raw_version}

        datadog_agent.reset()
        datadog_agent._config["enable_metadata_collection"] = enable_metadata_collection

        dd_run_check(gitlab_check(get_auth_config(use_openmetrics)))

        # With use_openmetrics, we also have a request to get the service checks.
        if enable_metadata_collection:
            assert g.call_count == (2 if use_openmetrics else 1)
            datadog_agent.assert_metadata('test:123', version_metadata)
            datadog_agent.assert_metadata_count(5)
        else:
            assert g.call_count == (1 if use_openmetrics else 0)
            datadog_agent.assert_metadata_count(0)
