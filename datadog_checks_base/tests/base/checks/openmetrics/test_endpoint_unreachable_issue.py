# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import errno
from io import BytesIO
from typing import Any
from unittest import mock

import pytest
import requests
from requests.exceptions import ProxyError as RequestsProxyError
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import MaxRetryError, NewConnectionError
from urllib3.exceptions import ProxyError as Urllib3ProxyError

from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics import endpoint_unreachable_issue
from datadog_checks.base.checks.openmetrics.endpoint_unreachable_issue import (
    ISSUE_ID_PREFIX,
    ISSUE_NAME,
    ISSUE_TYPE,
)

RAW_ENDPOINT = 'http://alice:s3cr3t@10.0.0.8:9102/metrics?token=secret'
SANITIZED_ENDPOINT = 'http://10.0.0.8:9102/metrics'
ISSUE_ID = f'{ISSUE_ID_PREFIX}:9fe9b88c342a66ef'
SECOND_ENDPOINT = 'http://10.0.0.9:9102/metrics'
SECOND_ISSUE_ID = f'{ISSUE_ID_PREFIX}:645abf3bffe9c583'
SECRETS = ('alice', 's3cr3t', 'token=secret')
WSAEHOSTUNREACH = 10065


def create_check(hostname: str = 'stubbed.hostname', name: str = 'openmetrics_test') -> mock.Mock:
    check = mock.Mock()
    check.hostname = hostname
    check.name = name
    check.IssueSeverity = {'MEDIUM': 2}
    return check


def unreachable_connection_error(endpoint: str = RAW_ENDPOINT) -> requests.ConnectionError:
    pool = HTTPConnectionPool('10.0.0.8', port=9102)
    connection_error = NewConnectionError(pool, 'Failed to establish a new connection')
    connection_error.__cause__ = OSError(errno.EHOSTUNREACH, 'No route to host')
    retry_error = MaxRetryError(pool, '/metrics', reason=connection_error)
    return requests.ConnectionError(f'GET {endpoint} failed', retry_error)


def unreachable_proxy_error() -> RequestsProxyError:
    pool = HTTPConnectionPool('proxy.example', port=8080)
    connection_error = NewConnectionError(pool, 'Failed to establish a new connection')
    connection_error.__cause__ = OSError(errno.EHOSTUNREACH, 'No route to host')
    proxy_error = Urllib3ProxyError('Unable to connect to proxy', connection_error)
    return RequestsProxyError(MaxRetryError(pool, RAW_ENDPOINT, reason=proxy_error))


def windows_error(error_code: int, winerror: int | None) -> requests.ConnectionError:
    error = OSError(error_code, 'A socket operation was attempted to an unreachable host')
    if winerror is not None:
        error.winerror = winerror
    return requests.ConnectionError(error)


def cyclic_context_error() -> RuntimeError:
    outer = RuntimeError('scrape failed')
    nested = RuntimeError('connection failed', OSError(errno.EHOSTUNREACH, 'No route to host'))
    outer.__context__ = nested
    nested.__context__ = outer
    return outer


def create_response(endpoint: str, status_code: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = endpoint
    response.raw = BytesIO()
    response.headers['Content-Type'] = 'text/plain'
    return response


def create_v2_check(*, ignore_connection_errors: bool = False) -> OpenMetricsBaseCheckV2:
    instance = {
        'openmetrics_endpoint': RAW_ENDPOINT,
        'namespace': 'demo',
        'metrics': [],
        'ignore_connection_errors': ignore_connection_errors,
    }
    check = OpenMetricsBaseCheckV2('openmetrics_test', {}, [instance])
    check.configure_scrapers()
    return check


def create_v1_check() -> tuple[OpenMetricsBaseCheck, dict]:
    instance = {'prometheus_url': RAW_ENDPOINT, 'namespace': 'demo', 'metrics': ['*']}
    check = OpenMetricsBaseCheck('openmetrics_test', {}, [instance])
    return check, check.get_scraper_config(instance)


def reported_issues(datadog_agent: Any) -> list[dict[str, Any]]:
    return datadog_agent._sent_reported_issues['openmetrics_test']


def test_report_submits_sanitized_issue_for_nested_no_route_error():
    check = create_check()

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')

    check.report_issue.assert_called_once()
    issue = check.report_issue.call_args.kwargs
    assert issue['id'] == ISSUE_ID
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == ISSUE_TYPE
    assert issue['title'] == f'OpenMetrics endpoint unreachable: {SANITIZED_ENDPOINT}'
    assert issue['category'] == 'integration'
    assert issue['severity'] == 2
    assert issue['extra'] == {
        'check_name': 'openmetrics_test',
        'endpoint': SANITIZED_ENDPOINT,
        'target_host': '10.0.0.8',
        'target_port': 9102,
        'target_path': '/metrics',
        'namespace': 'demo',
        'error_kind': 'no_route_to_host',
        'error_message': 'No route to host',
    }
    assert issue['tags'] == ['integration:openmetrics_test', 'openmetrics', 'endpoint-unreachable']
    assert all(secret not in repr(issue) for secret in SECRETS)


@pytest.mark.parametrize(
    ('endpoint', 'sanitized'),
    [
        pytest.param('http://example.test?verbose=1', 'http://example.test/', id='no-path'),
        pytest.param(
            "http://!$&'()*+,;=:@example.test/metrics?token=secret", 'http://example.test/metrics', id='userinfo'
        ),
        pytest.param('https://[::1]:9443/metrics#frag', 'https://[::1]:9443/metrics', id='ipv6'),
    ],
)
def test_report_sanitizes_the_endpoint(endpoint: str, sanitized: str):
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint))

    assert check.report_issue.call_args.kwargs['extra']['endpoint'] == sanitized


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(windows_error(WSAEHOSTUNREACH, None), id='winsock-errno'),
        pytest.param(windows_error(errno.EINVAL, WSAEHOSTUNREACH), id='winerror'),
        pytest.param(cyclic_context_error(), id='cyclic-context'),
    ],
)
def test_report_classifies_host_unreachable_errors(error: BaseException):
    check = create_check()

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, error)

    check.report_issue.assert_called_once()


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(OSError(errno.ECONNREFUSED, 'Connection refused'), id='connection-refused'),
        pytest.param(
            requests.ConnectionError('refused', OSError(errno.ECONNREFUSED, 'Connection refused')),
            id='wrapped-connection-refused',
        ),
        pytest.param(TimeoutError(errno.ETIMEDOUT, 'Connection timed out'), id='timeout'),
        pytest.param(RuntimeError(f'[Errno {errno.EHOSTUNREACH}] No route to host'), id='errno-only-in-text'),
        pytest.param(unreachable_proxy_error(), id='unreachable-proxy'),
    ],
)
def test_report_ignores_errors_other_than_no_route_to_the_endpoint(error: BaseException):
    check = create_check()

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, error)

    check.report_issue.assert_not_called()


def test_issue_id_is_stable_and_uses_every_identity_component():
    def report_id(
        hostname: str = 'stubbed.hostname',
        check_name: str = 'openmetrics_test',
        endpoint: str = RAW_ENDPOINT,
        namespace: str = 'demo',
    ) -> str:
        check = create_check(hostname, check_name)
        endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint), namespace)
        return check.report_issue.call_args.kwargs['id']

    assert report_id() == report_id() == ISSUE_ID
    changed_ids = {
        report_id(hostname='other.hostname'),
        report_id(check_name='other_openmetrics_test'),
        report_id(endpoint=RAW_ENDPOINT.replace('token=secret', 'token=other')),
        report_id(namespace='other'),
    }
    assert ISSUE_ID not in changed_ids
    assert len(changed_ids) == 4


def test_resolve_uses_the_reported_issue_id():
    check = create_check()

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')

    check.resolve_issue.assert_called_once_with(ISSUE_ID)


@pytest.mark.parametrize(
    'endpoint',
    [
        pytest.param(None, id='missing'),
        pytest.param('not a URL', id='not-a-url'),
        pytest.param('http://alice:s3cr3t@?token=secret', id='credentials-without-host'),
        pytest.param('http://example.test:invalid/metrics?token=secret', id='invalid-port'),
    ],
)
def test_invalid_endpoint_is_ignored(endpoint: str | None):
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, OSError(errno.EHOSTUNREACH, 'No route to host'))
    endpoint_unreachable_issue.resolve(check, endpoint)

    check.report_issue.assert_not_called()
    check.resolve_issue.assert_not_called()


def test_bridge_failures_do_not_raise():
    check = create_check()
    check.report_issue.side_effect = RuntimeError('report bridge failure')
    check.resolve_issue.side_effect = RuntimeError('resolve bridge failure')

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')


def test_v2_reports_no_route_error_and_preserves_the_scrape_error(datadog_agent):
    check = create_v2_check()
    error = unreachable_connection_error()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.check(None)

    assert str(exc_info.value) == f'There was an error scraping endpoint {RAW_ENDPOINT}: {error}'
    [issue] = reported_issues(datadog_agent)
    assert issue['id'] == ISSUE_ID


def test_v2_ignored_connection_error_does_not_report(datadog_agent):
    check = create_v2_check(ignore_connection_errors=True)
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error())

    check.check(None)

    assert reported_issues(datadog_agent) == []


def test_v2_any_response_resolves_before_status_handling(datadog_agent):
    check = create_v2_check()
    scraper = check.scrapers[RAW_ENDPOINT]
    scraper.send_request = mock.Mock(return_value=create_response(RAW_ENDPOINT, 500))

    with pytest.raises(requests.HTTPError):
        scraper.get_connection()

    datadog_agent.assert_resolved_issue(ISSUE_ID)


def test_v2_multiple_endpoints_report_only_the_failed_endpoint(datadog_agent):
    successful_config = {'openmetrics_endpoint': RAW_ENDPOINT, 'namespace': 'demo', 'metrics': []}
    failed_config = {'openmetrics_endpoint': SECOND_ENDPOINT, 'namespace': 'demo', 'metrics': []}
    check = OpenMetricsBaseCheckV2('openmetrics_test', {}, [successful_config])
    check.scraper_configs = [successful_config, failed_config]
    check.configure_scrapers()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(return_value=create_response(RAW_ENDPOINT))
    check.scrapers[SECOND_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error(SECOND_ENDPOINT))

    with pytest.raises(requests.ConnectionError):
        check.check(None)

    [issue] = reported_issues(datadog_agent)
    assert issue['id'] == SECOND_ISSUE_ID
    datadog_agent.assert_resolved_issue(ISSUE_ID)


def test_v1_reports_no_route_error_and_preserves_the_exception(datadog_agent):
    check, scraper_config = create_v1_check()
    error = unreachable_connection_error()
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    [issue] = reported_issues(datadog_agent)
    assert issue['id'] == ISSUE_ID


def test_v1_any_response_resolves_before_status_handling(datadog_agent):
    check, scraper_config = create_v1_check()
    check.send_request = mock.Mock(return_value=create_response(RAW_ENDPOINT, 500))

    with pytest.raises(requests.HTTPError):
        check.poll(scraper_config)

    datadog_agent.assert_resolved_issue(ISSUE_ID)
