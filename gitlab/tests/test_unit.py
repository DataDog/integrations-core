# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest
from mock.mock import MagicMock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab.common import get_gitlab_version

from .common import (
    CUSTOM_TAGS,
    GITALY_METRICS,
    GITLAB_GITALY_PROMETHEUS_ENDPOINT,
    GITLAB_SIDEKIQ_PROMETHEUS_ENDPOINT,
    GITLAB_TAGS,
    GITLAB_URL,
    GITLAB_WORKHORSE_PROMETHEUS_ENDPOINT,
    SIDEKIQ_EXPORTER_METRICS,
    V1_METRICS,
    V2_METRICS,
    WORKHORSE_METRICS,
    assert_check,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_check(dd_run_check, aggregator, mock_data, gitlab_check, get_config, use_openmetrics):
    check = gitlab_check(get_config(use_openmetrics))
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, V2_METRICS if use_openmetrics else V1_METRICS, use_openmetrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_gitaly(dd_run_check, aggregator, mock_data, gitlab_check, get_config):
    from datadog_checks.gitlab.gitlab_v2 import GitlabCheckV2

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


def test_check_workhorse_and_sidekiq_given_endpoints_configured_collects_their_metrics(
    dd_run_check, aggregator, mock_data, gitlab_check, get_config
):
    config = get_config(True)
    instance = config['instances'][0]
    instance["openmetrics_endpoint"] = instance["prometheus_url"]
    instance["workhorse_endpoint"] = GITLAB_WORKHORSE_PROMETHEUS_ENDPOINT
    instance["sidekiq_endpoint"] = GITLAB_SIDEKIQ_PROMETHEUS_ENDPOINT

    check = gitlab_check(config)
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, V2_METRICS + WORKHORSE_METRICS + SIDEKIQ_EXPORTER_METRICS, True)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    "raw_version",
    [
        "1.2.3",
        "5.6.7",
    ],
)
def test_get_gitlab_version(raw_version):
    http = FakeHTTPClient()
    http.register_response(
        'GET', 'http://localhost/api/v4/version', FakeHTTPResponse(json_result={"version": raw_version})
    )

    version = get_gitlab_version(http, MagicMock(), "http://localhost", "my-token")

    http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url='http://localhost/api/v4/version',
                options={'params': {'access_token': "my-token"}},
            )
        ]
    )
    assert version == raw_version


def test_get_gitlab_version_without_token():
    http = FakeHTTPClient()
    version = get_gitlab_version(http, MagicMock(), "http://localhost", None)
    http.assert_requests([])
    assert version is None


def test_no_gitlab_url(dd_run_check, aggregator, mock_data, gitlab_check, get_config):
    config = get_config(True)
    del config['instances'][0]['gitlab_url']
    check = gitlab_check(config)
    dd_run_check(check)
    aggregator.assert_service_check('gitlab.openmetrics.health', status=AgentCheck.OK)


def test_parse_readiness_service_checks_with_invalid_payload(
    dd_run_check, aggregator, mock_data, gitlab_check, get_config
):
    check = gitlab_check(get_config(True))
    # Manually init the check
    check.parse_config()

    response = FakeHTTPResponse(content=b'not json', json_error=json.JSONDecodeError('Expecting value', 'not json', 0))

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
    dd_run_check, aggregator, mock_data, gitlab_check, get_config, service_check, expected_redis_status
):
    check = gitlab_check(get_config(True))
    # Manually init the check
    check.parse_config()

    check.parse_readiness_service_checks(FakeHTTPResponse(json_result=service_check))

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
    datadog_agent,
    fake_http,
    fake_http_response,
    mock_data,
    raw_version,
    version_metadata,
    gitlab_check,
    get_config,
    enable_metadata_collection,
    use_openmetrics,
):
    version_url = '{}/api/v4/version'.format(GITLAB_URL)
    fake_http_response(version_url, json_data={'version': raw_version})
    config = get_config(use_openmetrics)
    config['instances'][0]['api_token'] = 'token'
    datadog_agent._config['enable_metadata_collection'] = enable_metadata_collection

    dd_run_check(gitlab_check(config))

    version_requests = [request for request in fake_http.requests if request.url == version_url]
    if enable_metadata_collection:
        assert len(version_requests) == 1
        datadog_agent.assert_metadata('test:123', version_metadata)
        datadog_agent.assert_metadata_count(5)
    else:
        assert version_requests == []
        datadog_agent.assert_metadata_count(0)
