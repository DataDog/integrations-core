# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock.mock import MagicMock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectTimeoutError, HTTPClientReadTimeoutError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab.common import get_gitlab_version
from datadog_checks.gitlab.gitlab_v2 import GitlabCheckV2

from .common import (
    CUSTOM_TAGS,
    GITALY_METRICS,
    GITLAB_GITALY_PROMETHEUS_ENDPOINT,
    GITLAB_HEALTH_ENDPOINT,
    GITLAB_LIVENESS_ENDPOINT,
    GITLAB_PROMETHEUS_ENDPOINT,
    GITLAB_READINESS_ENDPOINT,
    GITLAB_TAGS,
    V1_METRICS,
    V2_METRICS,
    assert_check,
)

pytestmark = [pytest.mark.unit]


def _expected_check_requests(
    *,
    use_openmetrics: bool,
    runs: int = 1,
    include_gitaly: bool = False,
    include_health: bool = True,
) -> list[RecordedRequest]:
    requests = []
    readiness_endpoint = '{}?all=1'.format(GITLAB_READINESS_ENDPOINT) if use_openmetrics else GITLAB_READINESS_ENDPOINT
    for _ in range(runs):
        requests.append(RecordedRequest('GET', GITLAB_PROMETHEUS_ENDPOINT, {'stream': True}))
        if include_gitaly:
            requests.append(RecordedRequest('GET', GITLAB_GITALY_PROMETHEUS_ENDPOINT, {'stream': True}))
        if include_health:
            requests.extend(
                [
                    RecordedRequest('GET', readiness_endpoint),
                    RecordedRequest('GET', GITLAB_LIVENESS_ENDPOINT),
                    RecordedRequest('GET', GITLAB_HEALTH_ENDPOINT),
                ]
            )

    return requests


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_check(dd_run_check, aggregator, mock_data, gitlab_check, get_config, use_openmetrics):
    fake_http = mock_data(use_openmetrics=use_openmetrics, runs=2)
    check = gitlab_check(get_config(use_openmetrics))
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, V2_METRICS if use_openmetrics else V1_METRICS, use_openmetrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    fake_http.assert_requests(_expected_check_requests(use_openmetrics=use_openmetrics, runs=2))
    fake_http.assert_all_responses_consumed()


def test_check_gitaly(dd_run_check, aggregator, mock_data, gitlab_check, get_config):
    fake_http = mock_data(use_openmetrics=True, runs=2, include_gitaly=True)
    config = get_config(True)
    instance = config['instances'][0]
    instance["openmetrics_endpoint"] = instance["prometheus_url"]
    instance["gitaly_server_endpoint"] = GITLAB_GITALY_PROMETHEUS_ENDPOINT

    check = gitlab_check(config)
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, V2_METRICS + GITALY_METRICS, True)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        'gitlab.gitaly.openmetrics.health',
        status=GitlabCheckV2.OK,
        tags=GITLAB_TAGS + CUSTOM_TAGS + ['endpoint:{}'.format(GITLAB_GITALY_PROMETHEUS_ENDPOINT)],
    )
    fake_http.assert_requests(_expected_check_requests(use_openmetrics=True, runs=2, include_gitaly=True))
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize(
    "raw_version",
    [
        "1.2.3",
        "5.6.7",
    ],
)
def test_get_gitlab_version(raw_version):
    http = FakeHTTPClient()
    url = "http://localhost/api/v4/version"
    options = {'params': {'access_token': "my-token"}}
    http.register_response(
        'GET',
        url,
        FakeHTTPResponse(json_result={"version": raw_version}),
        match_options=options,
    )

    version = get_gitlab_version(http, MagicMock(), "http://localhost", "my-token")

    assert version == raw_version
    http.assert_requests([RecordedRequest('GET', url, options)])
    http.assert_all_responses_consumed()


def test_get_gitlab_version_without_token():
    http = FakeHTTPClient()

    version = get_gitlab_version(http, MagicMock(), "http://localhost", None)

    assert version is None
    http.assert_requests([])
    http.assert_all_responses_consumed()


def test_no_gitlab_url(dd_run_check, aggregator, mock_data, gitlab_check, get_config):
    fake_http = mock_data(use_openmetrics=True, include_health=False)
    config = get_config(True)
    del config['instances'][0]['gitlab_url']
    check = gitlab_check(config)
    dd_run_check(check)
    aggregator.assert_service_check('gitlab.openmetrics.health', status=AgentCheck.OK)
    fake_http.assert_requests(_expected_check_requests(use_openmetrics=True, include_health=False))
    fake_http.assert_all_responses_consumed()


def test_parse_readiness_service_checks_with_invalid_payload(dd_run_check, aggregator, gitlab_check, get_config):
    check = gitlab_check(get_config(True))
    # Manually init the check
    check.parse_config()

    response = FakeHTTPResponse(json_error=ValueError("invalid readiness payload"))

    check.parse_readiness_service_checks(response)

    for service_check in check.READINESS_SERVICE_CHECKS.values():
        aggregator.assert_service_check(
            'gitlab.readiness.{}'.format(service_check), status=AgentCheck.UNKNOWN, tags=GITLAB_TAGS + CUSTOM_TAGS
        )

    assert len(aggregator.service_check_names) == 13


@pytest.mark.parametrize(
    'service_check, expected_redis_status',
    [
        pytest.param(
            {"redis_check": [{"status": "ok"}]},
            AgentCheck.OK,
            id="OK",
        ),
        pytest.param(
            {"redis_check": [{"status": "failed"}]},
            AgentCheck.CRITICAL,
            id="CRITICAL",
        ),
        pytest.param(
            {"redis_check": [{}]},
            AgentCheck.UNKNOWN,
            id="UNKNOWN",
        ),
        pytest.param(
            {},
            AgentCheck.UNKNOWN,
            id="missing service check",
        ),
        pytest.param(
            {"unknown_check": [{"status": "ok"}]},
            AgentCheck.UNKNOWN,
            id="unknown service check",
        ),
        pytest.param(
            {"redis": [{"status": "ok"}]},
            AgentCheck.UNKNOWN,
            id="service check not finishing with _check",
        ),
        pytest.param(
            {"redis_check": {"status": "ok"}},
            AgentCheck.UNKNOWN,
            id="malformed check",
        ),
    ],
)
def test_parse_readiness_service_checks(
    dd_run_check, aggregator, gitlab_check, get_config, service_check, expected_redis_status
):
    check = gitlab_check(get_config(True))
    # Manually init the check
    check.parse_config()

    response = FakeHTTPResponse(json_result=service_check)

    check.parse_readiness_service_checks(response)

    aggregator.assert_service_check(
        'gitlab.readiness.redis',
        status=expected_redis_status,
        tags=GITLAB_TAGS + CUSTOM_TAGS,
    )

    for not_received_service_check in set(check.READINESS_SERVICE_CHECKS.values()) - {"redis"}:
        aggregator.assert_service_check(
            'gitlab.readiness.{}'.format(not_received_service_check),
            status=AgentCheck.UNKNOWN,
            tags=GITLAB_TAGS + CUSTOM_TAGS,
        )

    assert len(aggregator.service_check_names) == 13


@pytest.mark.unit
@pytest.mark.parametrize('error_cls', [HTTPClientConnectTimeoutError, HTTPClientReadTimeoutError])
def test_prometheus_scrape_timeout_reports_critical(aggregator, gitlab_check, get_config, error_cls):
    check = gitlab_check(get_config(use_openmetrics=False))
    check.process = MagicMock(side_effect=error_cls("timed out"))
    check._check_health_endpoint = MagicMock()
    check.submit_version = MagicMock()

    check.check(None)

    aggregator.assert_service_check(check.PROMETHEUS_SERVICE_CHECK_NAME, status=AgentCheck.CRITICAL)
