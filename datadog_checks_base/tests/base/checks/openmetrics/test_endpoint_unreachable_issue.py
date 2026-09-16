# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import errno
import socket
from io import BytesIO
from unittest import mock

import pytest
import requests
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import MaxRetryError, NewConnectionError

from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.endpoint_unreachable_issue import (
    ISSUE_NAME,
    ISSUE_TYPE,
    EndpointUnreachableIssueReporter,
)

RAW_ENDPOINT = 'http://alice:s3cr3t@10.0.0.8:9102/metrics?token=secret'
SANITIZED_ENDPOINT = 'http://10.0.0.8:9102/metrics'
ISSUE_ID = 'openmetrics-endpoint-unreachable:9fe9b88c342a66ef'
SECOND_ENDPOINT = 'http://10.0.0.9:9102/metrics'


def create_check(hostname: str = 'stubbed.hostname', name: str = 'openmetrics_test') -> mock.Mock:
    check = mock.Mock()
    check.hostname = hostname
    check.name = name
    check.IssueSeverity = {'MEDIUM': 2}
    return check


def unreachable_connection_error(endpoint: str = RAW_ENDPOINT) -> requests.ConnectionError:
    pool = HTTPConnectionPool('10.0.0.8', port=9102)
    os_error = OSError(errno.EHOSTUNREACH, 'No route to host')
    connection_error = NewConnectionError(pool, 'Failed to establish a new connection')
    connection_error.__cause__ = os_error
    retry_error = MaxRetryError(pool, '/metrics', reason=connection_error)
    return requests.ConnectionError(f'GET {endpoint} failed', retry_error)


def create_response(endpoint: str, status_code: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = endpoint
    response.raw = BytesIO()
    response.headers['Content-Type'] = 'text/plain'
    return response


def create_v2_check(endpoint: str = RAW_ENDPOINT, *, ignore_connection_errors: bool = False) -> OpenMetricsBaseCheckV2:
    instance = {
        'openmetrics_endpoint': endpoint,
        'namespace': 'demo',
        'metrics': [],
        'ignore_connection_errors': ignore_connection_errors,
    }
    check = OpenMetricsBaseCheckV2('openmetrics_test', {}, [instance])
    check.configure_scrapers()
    return check


def create_v1_check(endpoint: str = RAW_ENDPOINT) -> tuple[OpenMetricsBaseCheck, dict]:
    instance = {'prometheus_url': endpoint, 'namespace': 'demo', 'metrics': ['*']}
    check = OpenMetricsBaseCheck('openmetrics_test', {}, [instance])
    return check, check.get_scraper_config(instance)


def test_report_submits_complete_sanitized_issue_for_nested_no_route_error():
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')

    check.report_issue.assert_called_once()
    issue = check.report_issue.call_args.kwargs
    assert issue == {
        'id': ISSUE_ID,
        'issue_name': ISSUE_NAME,
        'issue_type': ISSUE_TYPE,
        'title': f'OpenMetrics endpoint unreachable: {SANITIZED_ENDPOINT}',
        'description': (
            f'The openmetrics_test check cannot reach {SANITIZED_ENDPOINT} because no network route exists from '
            'the reporting Agent or Cluster Check Runner.'
        ),
        'category': 'integration',
        'severity': 2,
        'extra': {
            'check_name': 'openmetrics_test',
            'endpoint': SANITIZED_ENDPOINT,
            'target_host': '10.0.0.8',
            'target_port': 9102,
            'target_path': '/metrics',
            'namespace': 'demo',
            'error_kind': 'no_route_to_host',
            'error_message': mock.ANY,
        },
        'remediation': {
            'summary': (
                'Restore network reachability from the reporting Agent or Cluster Check Runner to this OpenMetrics '
                'endpoint, or correct a stale endpoint.'
            ),
            'steps': [
                {
                    'order': 1,
                    'text': (
                        'If 10.0.0.8 is a Kubernetes Pod IP, confirm it still belongs to a live pod. '
                        'Run: kubectl get pods -A -o wide --field-selector=status.podIP=10.0.0.8. '
                        'If no live pod owns it, inspect agent configcheck and fix stale Autodiscovery.'
                    ),
                },
                {
                    'order': 2,
                    'text': (
                        'Test from the reporting Agent or Cluster Check Runner network namespace. '
                        "Run: curl -sv --connect-timeout 5 'http://10.0.0.8:9102/metrics'."
                    ),
                },
                {
                    'order': 3,
                    'text': (
                        'Verify the target listener is on port 9102 and bound to the pod or host interface or 0.0.0.0. '
                        'For Envoy, test /stats/prometheus locally.'
                    ),
                },
                {
                    'order': 4,
                    'text': (
                        'If the endpoint is locally reachable, inspect firewall and security groups, Kubernetes '
                        'NetworkPolicy or Cilium policy, and cross-node CNI routing.'
                    ),
                },
                {
                    'order': 5,
                    'text': (
                        'From the same runner, use Run: agent check openmetrics_test. The issue resolves automatically '
                        'after the endpoint becomes reachable.'
                    ),
                },
            ],
        },
        'tags': ['integration:openmetrics_test', 'openmetrics', 'endpoint-unreachable'],
    }
    error_message = issue['extra']['error_message']
    assert f'[Errno {errno.EHOSTUNREACH}]' in error_message
    assert all(secret not in error_message for secret in ('alice', 's3cr3t', 'token=secret'))
    assert all('`' not in step['text'] for step in issue['remediation']['steps'])


def test_report_uses_flattened_errno_text_as_narrow_fallback():
    check = create_check()
    error = RuntimeError(f'scrape failed: [Errno {errno.EHOSTUNREACH}] No route to host')

    EndpointUnreachableIssueReporter.report(check, 'https://example.test/metrics', error)

    check.report_issue.assert_called_once()
    assert check.report_issue.call_args.kwargs['extra']['error_kind'] == 'no_route_to_host'


def test_exception_graph_walks_context_and_is_cycle_safe():
    check = create_check()
    outer = RuntimeError('scrape failed')
    nested = RuntimeError('connection failed')
    outer.__context__ = nested
    nested.__context__ = outer
    nested.args = (*nested.args, OSError(errno.EHOSTUNREACH, 'No route to host'))

    EndpointUnreachableIssueReporter.report(check, 'http://example.test/metrics', outer)

    check.report_issue.assert_called_once()


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(OSError(errno.ECONNREFUSED, 'Connection refused'), id='connection-refused'),
        pytest.param(TimeoutError(errno.ETIMEDOUT, 'Connection timed out'), id='timeout'),
        pytest.param(socket.gaierror(socket.EAI_NONAME, 'Name or service not known'), id='dns'),
        pytest.param(RuntimeError('[Errno 111] Connection refused'), id='unrelated-errno-text'),
        pytest.param(RuntimeError('unrelated scrape error'), id='unrelated-error'),
    ],
)
def test_report_ignores_errors_other_than_no_route_to_host(error: BaseException):
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, 'http://example.test/metrics', error)

    check.report_issue.assert_not_called()


def test_issue_identity_is_stable_and_uses_every_raw_identity_component():
    def report_id(
        hostname: str = 'stubbed.hostname',
        check_name: str = 'openmetrics_test',
        endpoint: str = RAW_ENDPOINT,
        namespace: str = 'demo',
    ) -> str:
        check = create_check(hostname, check_name)
        EndpointUnreachableIssueReporter.report(check, endpoint, unreachable_connection_error(endpoint), namespace)
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


def test_resolve_uses_the_same_raw_endpoint_identity():
    check = create_check()

    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace='demo')

    check.resolve_issue.assert_called_once_with(ISSUE_ID)


def test_report_and_resolve_bridge_failures_are_best_effort():
    check = create_check()
    check.report_issue.side_effect = RuntimeError('report bridge failure')
    check.resolve_issue.side_effect = RuntimeError('resolve bridge failure')

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace='demo')

    assert check.log.debug.call_count == 2


@pytest.mark.parametrize(
    'endpoint',
    [
        pytest.param(None, id='missing'),
        pytest.param('', id='empty'),
        pytest.param('not a URL', id='not-a-url'),
        pytest.param('http://alice:s3cr3t@?token=secret', id='credentials-without-host'),
        pytest.param('http://example.test:invalid/metrics?token=secret', id='invalid-port'),
    ],
)
def test_missing_or_invalid_endpoint_is_ignored_without_leaking_secrets(endpoint: str | None):
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, endpoint, OSError(errno.EHOSTUNREACH, 'No route to host'))
    EndpointUnreachableIssueReporter.resolve(check, endpoint)

    check.report_issue.assert_not_called()
    check.resolve_issue.assert_not_called()
    debug_output = repr(check.log.debug.call_args_list)
    assert all(secret not in debug_output for secret in ('alice', 's3cr3t', 'token=secret'))


def test_v2_check_reports_no_route_error_before_preserving_outer_error(datadog_agent):
    check = create_v2_check()
    error = unreachable_connection_error()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.check(None)

    assert str(exc_info.value) == f'There was an error scraping endpoint {RAW_ENDPOINT}: {error}'
    assert exc_info.value.__cause__ is None
    [issue] = datadog_agent._sent_reported_issues['openmetrics_test']
    assert issue['id'] == ISSUE_ID
    assert issue['extra']['endpoint'] == SANITIZED_ENDPOINT


def test_v2_ignored_connection_error_still_reports_issue(datadog_agent):
    check = create_v2_check(ignore_connection_errors=True)
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error())

    check.check(None)

    [issue] = datadog_agent._sent_reported_issues['openmetrics_test']
    assert issue['id'] == ISSUE_ID


@pytest.mark.parametrize('status_code', [pytest.param(200, id='success'), pytest.param(500, id='http-error')])
def test_v2_response_resolves_route_issue_before_status_handling(status_code, datadog_agent):
    check = create_v2_check()
    scraper = check.scrapers[RAW_ENDPOINT]
    response = create_response(RAW_ENDPOINT, status_code)
    scraper.send_request = mock.Mock(return_value=response)

    if status_code == 200:
        assert scraper.get_connection() is response
    else:
        with pytest.raises(requests.HTTPError):
            scraper.get_connection()

    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_v2_multiple_endpoints_report_only_failed_endpoint_with_distinct_id(datadog_agent):
    successful_config = {'openmetrics_endpoint': RAW_ENDPOINT, 'namespace': 'demo', 'metrics': []}
    failed_config = {'openmetrics_endpoint': SECOND_ENDPOINT, 'namespace': 'demo', 'metrics': []}
    check = OpenMetricsBaseCheckV2('openmetrics_test', {}, [successful_config])
    check.scraper_configs = [successful_config, failed_config]
    check.configure_scrapers()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(return_value=create_response(RAW_ENDPOINT))
    check.scrapers[SECOND_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error(SECOND_ENDPOINT))

    with pytest.raises(requests.ConnectionError):
        check.check(None)

    [issue] = datadog_agent._sent_reported_issues['openmetrics_test']
    assert issue['extra']['endpoint'] == SECOND_ENDPOINT
    assert len(datadog_agent._sent_resolved_issues) == 1
    assert issue['id'] != datadog_agent._sent_resolved_issues[0]


def test_v1_poll_reports_no_route_error_and_preserves_exception(datadog_agent):
    check, scraper_config = create_v1_check()
    error = unreachable_connection_error()
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    [issue] = datadog_agent._sent_reported_issues['openmetrics_test']
    assert issue['id'] == ISSUE_ID


@pytest.mark.parametrize('status_code', [pytest.param(200, id='success'), pytest.param(500, id='http-error')])
def test_v1_response_resolves_route_issue_before_status_handling(status_code, datadog_agent):
    check, scraper_config = create_v1_check()
    response = create_response(RAW_ENDPOINT, status_code)
    check.send_request = mock.Mock(return_value=response)

    if status_code == 200:
        assert check.poll(scraper_config) is response
    else:
        with pytest.raises(requests.HTTPError):
            check.poll(scraper_config)

    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_non_no_route_connection_error_does_not_report(datadog_agent):
    check, scraper_config = create_v1_check()
    error = requests.ConnectionError('connection refused', OSError(errno.ECONNREFUSED, 'Connection refused'))
    reporter = mock.Mock(wraps=EndpointUnreachableIssueReporter)
    check.endpoint_unreachable_issue_reporter = reporter
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    reporter.report.assert_called_once_with(check, RAW_ENDPOINT, error, 'demo')
    assert not datadog_agent._sent_reported_issues


def test_reporter_bridge_failure_does_not_mask_scrape_error():
    check, scraper_config = create_v1_check()
    error = unreachable_connection_error()
    check.report_issue = mock.Mock(side_effect=RuntimeError('report bridge failure'))
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    check.report_issue.assert_called_once()


def test_resolver_bridge_failure_does_not_fail_successful_scrape():
    check = create_v2_check()
    response = create_response(RAW_ENDPOINT)
    check.resolve_issue = mock.Mock(side_effect=RuntimeError('resolve bridge failure'))
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(return_value=response)

    assert check.scrapers[RAW_ENDPOINT].get_connection() is response
    check.resolve_issue.assert_called_once_with(ISSUE_ID)
