# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import errno
import shlex
from io import BytesIO
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
ENVOY_ISSUE_ID = f'{ISSUE_ID_PREFIX}:2d001d82e5465988'
DEFAULT_NAMESPACE_ISSUE_ID = f'{ISSUE_ID_PREFIX}:a8006c4341ad9679'
CANONICAL_ERROR_MESSAGE = 'No route to host'
WSAEHOSTUNREACH = 10065


class Namespace:
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value


class NamespacedV2Check(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'envoy'


class DefaultNamespaceV2Check(OpenMetricsBaseCheckV2):
    def get_default_config(self) -> dict:
        return {'namespace': 'default-demo'}


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


def unreachable_proxy_error(endpoint: str = RAW_ENDPOINT) -> RequestsProxyError:
    pool = HTTPConnectionPool('proxy.example', port=8080)
    os_error = OSError(errno.EHOSTUNREACH, 'No route to host')
    connection_error = NewConnectionError(pool, 'Failed to establish a new connection')
    connection_error.__cause__ = os_error
    proxy_error = Urllib3ProxyError('Unable to connect to proxy', connection_error)
    retry_error = MaxRetryError(pool, endpoint, reason=proxy_error)
    return RequestsProxyError(retry_error)


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

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')

    check.report_issue.assert_called_once()
    issue = check.report_issue.call_args.kwargs
    assert issue['id'] == ISSUE_ID
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == ISSUE_TYPE
    assert issue['title'] == f'OpenMetrics endpoint unreachable: {SANITIZED_ENDPOINT}'
    assert issue['description'] == (
        f'The openmetrics_test check cannot reach {SANITIZED_ENDPOINT} because no network route exists from '
        'the reporting Agent or Cluster Check Runner.'
    )
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
        'error_message': CANONICAL_ERROR_MESSAGE,
    }
    assert issue['tags'] == ['integration:openmetrics_test', 'openmetrics', 'endpoint-unreachable']
    assert issue['remediation']['summary'] == (
        'Restore network reachability from the reporting Agent or Cluster Check Runner to this OpenMetrics endpoint, '
        'or correct a stale endpoint.'
    )
    steps = issue['remediation']['steps']
    assert [step['order'] for step in steps] == list(range(1, 6))
    step_texts = [step['text'] for step in steps]
    assert 'kubectl get pods -A -o wide --field-selector=status.podIP=10.0.0.8' in step_texts[0]
    assert 'curl -sv --connect-timeout 5 http://10.0.0.8:9102/metrics' in step_texts[1]
    assert 'target listener' in step_texts[2]
    assert 'NetworkPolicy or Cilium policy' in step_texts[3]
    assert 'resolves automatically' in step_texts[4]
    assert 'agent check openmetrics_test' in step_texts[4]
    emitted_issue = repr(issue)
    assert all(secret not in emitted_issue for secret in ('alice', 's3cr3t', 'token=secret'))
    assert '`' not in emitted_issue


def test_report_emits_canonical_error_without_url_leakage_or_corruption():
    endpoint = "http://!$&'()*+,;=:@example.test/metrics?token=secret"
    sanitized_endpoint = 'http://example.test/metrics'
    url_secret = "!$&'()*+,;=:@"
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint))

    issue = check.report_issue.call_args.kwargs
    assert issue['extra']['endpoint'] == sanitized_endpoint
    assert issue['extra']['target_path'] == sanitized_endpoint.removeprefix('http://example.test')
    assert issue['extra']['error_message'] == CANONICAL_ERROR_MESSAGE
    emitted_issue = repr(issue)
    assert endpoint not in emitted_issue
    assert url_secret not in emitted_issue


def test_report_normalizes_an_endpoint_without_a_path():
    check = create_check()

    endpoint_unreachable_issue.report(
        check,
        'http://example.test?verbose=1',
        unreachable_connection_error(),
    )

    issue = check.report_issue.call_args.kwargs
    assert issue['extra']['endpoint'] == 'http://example.test/'
    assert issue['extra']['target_path'] == '/'
    assert issue['remediation']['steps'][1]['text'].endswith('curl -sv --connect-timeout 5 http://example.test/')


def test_remediation_shell_quotes_the_endpoint():
    endpoint = "http://10.0.0.8/'; echo PWNED; #'"
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint))

    issue = check.report_issue.call_args.kwargs
    sanitized_endpoint = issue['extra']['endpoint']
    curl_step = issue['remediation']['steps'][1]['text']
    command = curl_step.split('Run: ', 1)[1]
    assert shlex.split(command) == ['curl', '-sv', '--connect-timeout', '5', sanitized_endpoint]


def test_remediation_does_not_put_an_unvalidated_host_in_a_kubectl_command():
    endpoint = 'http://10.0.0.8;id;/metrics'
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint))

    step = check.report_issue.call_args.kwargs['remediation']['steps'][0]['text']
    assert 'kubectl' not in step
    assert step.endswith('Run: agent configcheck')


def test_remediation_does_not_treat_a_scoped_ipv6_host_as_a_pod_ip():
    endpoint = 'http://[fe80::1%25$(id)]/metrics'
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, unreachable_connection_error(endpoint))

    step = check.report_issue.call_args.kwargs['remediation']['steps'][0]['text']
    assert 'kubectl' not in step
    assert '$(id)' not in step
    assert step.endswith('Run: agent configcheck')


@pytest.mark.parametrize('check_name', ['openmetrics; echo PWNED', '--help'])
def test_remediation_does_not_interpolate_an_unsafe_check_name(check_name: str):
    check = create_check(name=check_name)

    endpoint_unreachable_issue.report(check, SANITIZED_ENDPOINT, unreachable_connection_error())

    step = check.report_issue.call_args.kwargs['remediation']['steps'][4]['text']
    assert check_name not in step
    assert 'agent check' not in step


def test_report_does_not_classify_errno_text_in_the_request_url():
    check = create_check()
    endpoint = f'http://example.test/[Errno {errno.EHOSTUNREACH}]/metrics'
    error = requests.ConnectionError(
        f'GET {endpoint} failed',
        OSError(errno.ECONNREFUSED, 'Connection refused'),
    )

    endpoint_unreachable_issue.report(check, endpoint, error)

    check.report_issue.assert_not_called()


def test_report_does_not_attribute_an_unreachable_proxy_to_the_endpoint():
    check = create_check()

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_proxy_error())

    check.report_issue.assert_not_called()


@pytest.mark.parametrize(
    ('error_code', 'winerror'),
    [
        pytest.param(WSAEHOSTUNREACH, None, id='winsock-errno'),
        pytest.param(errno.EINVAL, WSAEHOSTUNREACH, id='winerror'),
    ],
)
def test_report_classifies_windows_host_unreachable_error(error_code: int, winerror: int | None):
    check = create_check()
    error = OSError(error_code, 'A socket operation was attempted to an unreachable host')
    if winerror is not None:
        error.winerror = winerror

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, requests.ConnectionError(error))

    check.report_issue.assert_called_once()
    assert check.report_issue.call_args.kwargs['extra']['error_message'] == CANONICAL_ERROR_MESSAGE


def test_exception_graph_walks_context_and_is_cycle_safe():
    check = create_check()
    outer = RuntimeError('scrape failed')
    nested = RuntimeError('connection failed')
    outer.__context__ = nested
    nested.__context__ = outer
    nested.args = (*nested.args, OSError(errno.EHOSTUNREACH, 'No route to host'))

    endpoint_unreachable_issue.report(check, 'http://example.test/metrics', outer)

    check.report_issue.assert_called_once()


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(OSError(errno.ECONNREFUSED, 'Connection refused'), id='connection-refused'),
        pytest.param(TimeoutError(errno.ETIMEDOUT, 'Connection timed out'), id='timeout'),
        pytest.param(
            RuntimeError(f'[Errno {errno.EHOSTUNREACH}] No route to host'),
            id='flattened-host-unreachable-text',
        ),
    ],
)
def test_report_ignores_errors_other_than_no_route_to_host(error: BaseException):
    check = create_check()

    endpoint_unreachable_issue.report(check, 'http://example.test/metrics', error)

    check.report_issue.assert_not_called()


def test_issue_identity_is_stable_and_uses_every_raw_identity_component():
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


def test_resolve_uses_the_same_raw_endpoint_identity():
    check = create_check()

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')

    check.resolve_issue.assert_called_once_with(ISSUE_ID)


def test_resolve_crosses_the_bridge_once_until_the_issue_is_reported_again():
    check = create_check()

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')

    assert check.resolve_issue.call_args_list == [mock.call(ISSUE_ID), mock.call(ISSUE_ID)]


def test_failed_untracked_resolve_is_retried():
    check = create_check()
    check.resolve_issue.side_effect = [RuntimeError('resolve bridge failure'), None]

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')

    assert check.resolve_issue.call_args_list == [mock.call(ISSUE_ID), mock.call(ISSUE_ID)]


@pytest.mark.parametrize('initialize_state', [False, True], ids=['no-state', 'empty-state'])
def test_resolve_stale_does_not_consume_endpoints_when_no_issues_are_tracked(initialize_state: bool):
    check = create_check()
    iterations = 0

    if initialize_state:
        endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
        check.resolve_issue.reset_mock()

    def active_endpoints():
        nonlocal iterations
        iterations += 1
        yield RAW_ENDPOINT, 'demo'

    endpoint_unreachable_issue.resolve_stale(check, active_endpoints())

    assert iterations == 0
    check.resolve_issue.assert_not_called()


def test_endpoint_returning_after_stale_resolution_is_reconciled_again():
    check = create_check()
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')

    endpoint_unreachable_issue.resolve_stale(check, ())
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')

    assert check.resolve_issue.call_args_list == [mock.call(ISSUE_ID), mock.call(ISSUE_ID)]


def test_cancel_drains_exact_reported_issue_and_suppresses_late_reports():
    check = create_check()
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    endpoint_unreachable_issue.cancel(check)
    endpoint_unreachable_issue.report(
        check,
        SECOND_ENDPOINT,
        unreachable_connection_error(SECOND_ENDPOINT),
        namespace='demo',
    )

    check.resolve_issue.assert_called_once_with(issue_id)
    check.report_issue.assert_called_once()


def test_successful_resolve_removes_tracked_issue_before_cancel():
    check = create_check()
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.cancel(check)

    check.resolve_issue.assert_called_once_with(issue_id)


def test_failed_resolve_leaves_tracked_issue_for_cancellation_retry():
    check = create_check()
    check.resolve_issue.side_effect = [RuntimeError('resolve bridge failure'), None]
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.cancel(check)

    assert check.resolve_issue.call_args_list == [mock.call(issue_id), mock.call(issue_id)]


def test_namespace_is_normalized_for_identity_and_emitted_context():
    check = create_check()
    namespace = Namespace('demo')

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace)
    issue = check.report_issue.call_args.kwargs
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace)

    assert issue['extra']['namespace'] == 'demo'
    check.resolve_issue.assert_called_once_with(issue['id'])


def test_report_and_resolve_bridge_failures_are_best_effort():
    check = create_check()
    check.report_issue.side_effect = [RuntimeError('report bridge failure'), None]
    check.resolve_issue.side_effect = RuntimeError('resolve bridge failure')

    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    endpoint_unreachable_issue.resolve(check, RAW_ENDPOINT, namespace='demo')
    endpoint_unreachable_issue.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')

    assert [call.kwargs['id'] for call in check.report_issue.call_args_list] == [ISSUE_ID, ISSUE_ID]


@pytest.mark.parametrize(
    'endpoint',
    [
        pytest.param(None, id='missing'),
        pytest.param('not a URL', id='not-a-url'),
        pytest.param('http://alice:s3cr3t@?token=secret', id='credentials-without-host'),
        pytest.param('http://example.test:invalid/metrics?token=secret', id='invalid-port'),
        pytest.param('http://example.test:0/metrics', id='http-zero-port'),
    ],
)
def test_missing_or_invalid_endpoint_is_ignored_without_leaking_secrets(endpoint: str | None):
    check = create_check()

    endpoint_unreachable_issue.report(check, endpoint, OSError(errno.EHOSTUNREACH, 'No route to host'))
    endpoint_unreachable_issue.resolve(check, endpoint)

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
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)
    assert issue['extra']['endpoint'] == SANITIZED_ENDPOINT


def test_v2_ignored_connection_error_does_not_report_issue(datadog_agent):
    check = create_v2_check(ignore_connection_errors=True)
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error())

    check.check(None)

    datadog_agent.assert_no_reported_issues()


def test_v2_ignored_connection_error_resolves_an_existing_issue(datadog_agent):
    check = create_v2_check()
    scraper = check.scrapers[RAW_ENDPOINT]
    scraper.send_request = mock.Mock(side_effect=unreachable_connection_error())
    with pytest.raises(requests.ConnectionError):
        check.check(None)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)

    scraper.ignore_connection_errors = True
    check.check(None)

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_reported_issue_count('openmetrics_test', 1)


def test_v2_cancel_resolves_issue_for_an_unscheduled_stale_endpoint(datadog_agent):
    check = create_v2_check()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error())
    with pytest.raises(requests.ConnectionError):
        check.check(None)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)

    check.cancel()

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


@pytest.mark.parametrize(
    ('check_class', 'check_name', 'endpoint_option', 'configured_namespace', 'namespace', 'issue_id'),
    [
        pytest.param(
            NamespacedV2Check,
            'envoy',
            'openmetrics_endpoint',
            None,
            'envoy',
            ENVOY_ISSUE_ID,
            id='class-namespace',
        ),
        pytest.param(
            DefaultNamespaceV2Check,
            'openmetrics_test',
            'openmetrics_endpoint',
            None,
            'default-demo',
            DEFAULT_NAMESPACE_ISSUE_ID,
            id='default-namespace',
        ),
        pytest.param(
            OpenMetricsBaseCheckV2,
            'openmetrics_test',
            'agent_endpoint',
            'demo',
            'demo',
            ISSUE_ID,
            id='generated-endpoint',
        ),
    ],
)
def test_v2_cancel_resolves_process_isolation_endpoint_from_config(
    check_class: type[OpenMetricsBaseCheckV2],
    check_name: str,
    endpoint_option: str,
    configured_namespace: str | None,
    namespace: str,
    issue_id: str,
    datadog_agent,
):
    instance = {endpoint_option: RAW_ENDPOINT, 'metrics': [], 'process_isolation': True}
    if configured_namespace is not None:
        instance['namespace'] = configured_namespace
    check = check_class(check_name, {}, [instance])
    child_check = check_class(
        check_name,
        {},
        [{key: value for key, value in instance.items() if key != 'process_isolation'}],
    )
    endpoint_unreachable_issue.report(
        child_check,
        RAW_ENDPOINT,
        unreachable_connection_error(),
        namespace,
    )
    datadog_agent.assert_reported_issue(check_name, issue_id)

    check.cancel()

    datadog_agent.assert_resolved_issue(issue_id)
    datadog_agent.assert_resolved_issue_count(1)


def test_v2_refresh_resolves_reported_issue_for_removed_dynamic_endpoint(datadog_agent):
    check = create_v2_check()
    check.scrapers[RAW_ENDPOINT].send_request = mock.Mock(side_effect=unreachable_connection_error())
    with pytest.raises(requests.ConnectionError):
        check.check(None)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)

    replacement_scraper = mock.Mock()
    replacement_scraper.endpoint = SECOND_ENDPOINT
    replacement_scraper.namespace = 'demo'
    check.refresh_scrapers = mock.Mock(
        side_effect=lambda: setattr(check, 'scrapers', {SECOND_ENDPOINT: replacement_scraper})
    )

    check.check(None)

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


def test_v2_response_resolves_route_issue_before_status_handling(datadog_agent):
    check = create_v2_check()
    scraper = check.scrapers[RAW_ENDPOINT]
    response = create_response(RAW_ENDPOINT, 500)
    scraper.send_request = mock.Mock(return_value=response)

    with pytest.raises(requests.HTTPError):
        scraper.get_connection()

    datadog_agent.assert_resolved_issue(ISSUE_ID)


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

    issue = datadog_agent.assert_reported_issue('openmetrics_test', SECOND_ISSUE_ID)
    assert issue['extra']['endpoint'] == SECOND_ENDPOINT
    datadog_agent.assert_reported_issue_count('openmetrics_test', 1)
    datadog_agent.assert_resolved_issue(ISSUE_ID)
    datadog_agent.assert_resolved_issue_count(1)


def test_v1_poll_reports_no_route_error_and_preserves_exception(datadog_agent):
    check, scraper_config = create_v1_check()
    error = unreachable_connection_error()
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)


def test_v1_cancel_resolves_issue_for_an_unscheduled_stale_endpoint(datadog_agent):
    check, scraper_config = create_v1_check()
    check.send_request = mock.Mock(side_effect=unreachable_connection_error())
    with pytest.raises(requests.ConnectionError):
        check.poll(scraper_config)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)

    check.cancel()

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


def test_v1_cancel_resolves_exact_issue_after_runtime_endpoint_mutation(datadog_agent):
    check, scraper_config = create_v1_check()
    scraper_config['prometheus_url'] = SECOND_ENDPOINT
    check.send_request = mock.Mock(side_effect=unreachable_connection_error(SECOND_ENDPOINT))
    with pytest.raises(requests.ConnectionError):
        check.poll(scraper_config)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', SECOND_ISSUE_ID)

    check.cancel()

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


def test_v1_cancel_uses_runtime_config_endpoint_for_process_isolation_fallback(datadog_agent):
    instance = {
        'prometheus_url': RAW_ENDPOINT,
        'namespace': 'demo',
        'metrics': ['*'],
        'process_isolation': True,
    }
    check = OpenMetricsBaseCheck('openmetrics_test', {}, [instance])
    check.config_map[RAW_ENDPOINT]['prometheus_url'] = SECOND_ENDPOINT
    child_check = OpenMetricsBaseCheck(
        'openmetrics_test',
        {},
        [{**instance, 'prometheus_url': SECOND_ENDPOINT, 'process_isolation': False}],
    )
    endpoint_unreachable_issue.report(
        child_check,
        SECOND_ENDPOINT,
        unreachable_connection_error(SECOND_ENDPOINT),
        'demo',
    )
    issue = datadog_agent.assert_reported_issue('openmetrics_test', SECOND_ISSUE_ID)

    check.cancel()

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


def test_report_racing_with_cancel_is_immediately_resolved_and_not_retained(datadog_agent):
    check, scraper_config = create_v1_check()
    original_report_issue = check.report_issue

    def report_then_cancel(**kwargs: object) -> None:
        original_report_issue(**kwargs)
        check.cancel()

    check.report_issue = report_then_cancel
    check.send_request = mock.Mock(side_effect=unreachable_connection_error())

    with pytest.raises(requests.ConnectionError):
        check.poll(scraper_config)
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)
    check.cancel()

    datadog_agent.assert_resolved_issue(issue['id'])
    datadog_agent.assert_resolved_issue_count(1)


def test_v1_response_resolves_route_issue_before_status_handling(datadog_agent):
    check, scraper_config = create_v1_check()
    response = create_response(RAW_ENDPOINT, 500)
    check.send_request = mock.Mock(return_value=response)

    with pytest.raises(requests.HTTPError):
        check.poll(scraper_config)

    datadog_agent.assert_resolved_issue(ISSUE_ID)


def test_non_no_route_connection_error_does_not_report(datadog_agent):
    check, scraper_config = create_v1_check()
    error = requests.ConnectionError('connection refused', OSError(errno.ECONNREFUSED, 'Connection refused'))
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    datadog_agent.assert_no_reported_issues()
