# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
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

    with pytest.raises(HTTPClientConnectionError):
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


def test_connection_failure_openmetrics(dd_run_check, aggregator, gitlab_check, get_bad_config):
    check = gitlab_check(get_bad_config(True))

    with pytest.raises(Exception, match="HTTPClientConnectionError"):
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
