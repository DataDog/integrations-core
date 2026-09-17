# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import errno
import shlex
import socket
from io import BytesIO
from unittest import mock

import pytest
import requests
from requests.exceptions import ProxyError as RequestsProxyError
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import MaxRetryError, NewConnectionError
from urllib3.exceptions import ProxyError as Urllib3ProxyError

from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.checks.openmetrics.endpoint_unreachable_issue import (
    ISSUE_ID_PREFIX,
    ISSUE_NAME,
    ISSUE_TYPE,
    EndpointUnreachableIssueReporter,
)
from datadog_checks.base.checks.openmetrics.mixins import OpenMetricsScraperMixin
from datadog_checks.base.checks.openmetrics.v2.scraper.base_scraper import OpenMetricsScraper
from datadog_checks.base.constants import ServiceCheck

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


class CheckWithoutEndpointReporter:
    def __init__(self):
        self.name = 'openmetrics_test'
        self.IssueSeverity = {'MEDIUM': 2}
        self.log = mock.Mock()
        self.report_issue = mock.Mock()
        self.resolve_issue = mock.Mock()
        self.service_check = mock.Mock()
        self.gauge = mock.Mock()

    @property
    def hostname(self) -> str:
        return 'stubbed.hostname'


class V1MixinConsumer(OpenMetricsScraperMixin, CheckWithoutEndpointReporter):
    def __init__(self):
        super().__init__()


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


def create_v1_scraper_config(endpoint: str = RAW_ENDPOINT) -> dict:
    return {
        'prometheus_url': endpoint,
        'namespace': 'demo',
        'health_service_check': True,
        'custom_tags': [],
    }


def create_v2_scraper_without_reporter() -> tuple[OpenMetricsScraper, OpenMetricsBaseCheckV2]:
    check = create_v2_check()
    scraper = check.scrapers[RAW_ENDPOINT]
    del check.endpoint_unreachable_issue_reporter
    return scraper, check


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
                        'If 10.0.0.8 is a Kubernetes Pod IP, confirm it still belongs to a live pod. If no live pod '
                        'owns it, inspect agent configcheck and fix stale Autodiscovery. To list matching pods, run: '
                        'kubectl get pods -A -o wide --field-selector=status.podIP=10.0.0.8'
                    ),
                },
                {
                    'order': 2,
                    'text': (
                        'Test from the reporting Agent or Cluster Check Runner network namespace. '
                        'Run: curl -sv --connect-timeout 5 http://10.0.0.8:9102/metrics'
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
                        'The issue resolves automatically after the endpoint becomes reachable. To verify from the '
                        'same reporting Agent or Cluster Check Runner, run: agent check openmetrics_test'
                    ),
                },
            ],
        },
        'tags': ['integration:openmetrics_test', 'openmetrics', 'endpoint-unreachable'],
    }
    error_message = issue['extra']['error_message']
    assert error_message == CANONICAL_ERROR_MESSAGE
    assert 'secret' not in error_message
    assert all('`' not in step['text'] for step in issue['remediation']['steps'])


@pytest.mark.parametrize(
    ('endpoint', 'sanitized_endpoint', 'url_secret'),
    [
        pytest.param(
            'http://example.test?verbose=1',
            'http://example.test/',
            'verbose=1',
            id='short-query-value',
        ),
        pytest.param('http://:@example.test', 'http://example.test/', ':@', id='empty-userinfo'),
        pytest.param(
            "http://!$&'()*+,;=:@example.test/metrics?token=secret",
            'http://example.test/metrics',
            "!$&'()*+,;=:@",
            id='punctuation-only-userinfo',
        ),
    ],
)
def test_report_emits_canonical_error_without_url_leakage_or_corruption(
    endpoint: str, sanitized_endpoint: str, url_secret: str
):
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, endpoint, unreachable_connection_error(endpoint))

    issue = check.report_issue.call_args.kwargs
    assert issue['extra']['endpoint'] == sanitized_endpoint
    assert issue['extra']['target_path'] == sanitized_endpoint.removeprefix('http://example.test')
    assert issue['extra']['error_message'] == CANONICAL_ERROR_MESSAGE
    emitted_issue = repr(issue)
    assert endpoint not in emitted_issue
    assert url_secret not in emitted_issue


@pytest.mark.parametrize(
    'endpoint',
    [
        pytest.param("http://10.0.0.8/'; echo PWNED; #'", id='single-quote'),
        pytest.param('http://10.0.0.8/$(echo PWNED)', id='command-substitution'),
        pytest.param('http://10.0.0.8/metrics;echo${IFS}PWNED', id='semicolon'),
    ],
)
def test_remediation_shell_quotes_the_endpoint(endpoint: str):
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, endpoint, unreachable_connection_error(endpoint))

    issue = check.report_issue.call_args.kwargs
    sanitized_endpoint = issue['extra']['endpoint']
    curl_step = issue['remediation']['steps'][1]['text']
    command = curl_step.split('Run: ', 1)[1]
    assert shlex.split(command) == ['curl', '-sv', '--connect-timeout', '5', sanitized_endpoint]


def test_remediation_does_not_put_an_unvalidated_host_in_a_kubectl_command():
    endpoint = 'http://10.0.0.8;id;/metrics'
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, endpoint, unreachable_connection_error(endpoint))

    step = check.report_issue.call_args.kwargs['remediation']['steps'][0]['text']
    assert 'kubectl' not in step
    assert step.endswith('Run: agent configcheck')


@pytest.mark.parametrize(
    ('endpoint', 'unsafe_text'),
    [
        pytest.param('http://[fe80::1%25$(id)]/metrics', '$(id)', id='command-substitution'),
        pytest.param(
            'http://[fe80::1%25eth0,metadata.name=x]/metrics',
            'metadata.name=x',
            id='field-selector',
        ),
    ],
)
def test_remediation_does_not_treat_a_scoped_ipv6_host_as_a_pod_ip(endpoint: str, unsafe_text: str):
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, endpoint, unreachable_connection_error(endpoint))

    step = check.report_issue.call_args.kwargs['remediation']['steps'][0]['text']
    assert 'kubectl' not in step
    assert unsafe_text not in step
    assert step.endswith('Run: agent configcheck')


@pytest.mark.parametrize('check_name', ['openmetrics; echo PWNED', '--help'])
def test_remediation_does_not_interpolate_an_unsafe_check_name(check_name: str):
    check = create_check(name=check_name)

    EndpointUnreachableIssueReporter.report(check, SANITIZED_ENDPOINT, unreachable_connection_error())

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

    EndpointUnreachableIssueReporter.report(check, endpoint, error)

    check.report_issue.assert_not_called()


def test_report_does_not_attribute_an_unreachable_proxy_to_the_endpoint():
    check = create_check()

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_proxy_error())

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

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, requests.ConnectionError(error))

    check.report_issue.assert_called_once()
    assert check.report_issue.call_args.kwargs['extra']['error_message'] == CANONICAL_ERROR_MESSAGE


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
        pytest.param(
            RuntimeError(f'[Errno {errno.EHOSTUNREACH}] No route to host'),
            id='flattened-host-unreachable-text',
        ),
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


def test_cancel_drains_exact_reported_issue_and_suppresses_late_reports():
    check = create_check()
    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    EndpointUnreachableIssueReporter.cancel(check)
    EndpointUnreachableIssueReporter.report(
        check,
        SECOND_ENDPOINT,
        unreachable_connection_error(SECOND_ENDPOINT),
        namespace='demo',
    )

    check.resolve_issue.assert_called_once_with(issue_id)
    check.report_issue.assert_called_once()


def test_successful_resolve_removes_tracked_issue_before_cancel():
    check = create_check()
    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace='demo')
    EndpointUnreachableIssueReporter.cancel(check)

    check.resolve_issue.assert_called_once_with(issue_id)


def test_failed_resolve_leaves_tracked_issue_for_cancellation_retry():
    check = create_check()
    check.resolve_issue.side_effect = [RuntimeError('resolve bridge failure'), None]
    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    issue_id = check.report_issue.call_args.kwargs['id']

    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace='demo')
    EndpointUnreachableIssueReporter.cancel(check)

    assert check.resolve_issue.call_args_list == [mock.call(issue_id), mock.call(issue_id)]


def test_namespace_is_normalized_for_identity_and_emitted_context():
    check = create_check()
    namespace = Namespace('demo')

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace)
    issue = check.report_issue.call_args.kwargs
    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace)

    assert issue['extra']['namespace'] == 'demo'
    check.resolve_issue.assert_called_once_with(issue['id'])


def test_report_and_resolve_bridge_failures_are_best_effort():
    check = create_check()
    check.report_issue.side_effect = RuntimeError('report bridge failure')
    check.resolve_issue.side_effect = RuntimeError('resolve bridge failure')

    EndpointUnreachableIssueReporter.report(check, RAW_ENDPOINT, unreachable_connection_error(), namespace='demo')
    EndpointUnreachableIssueReporter.resolve(check, RAW_ENDPOINT, namespace='demo')

    assert check.log.debug.call_args_list == [
        mock.call('Failed to report the OpenMetrics endpoint-unreachable issue', exc_info=True),
        mock.call('Failed to resolve the OpenMetrics endpoint-unreachable issue', exc_info=True),
    ]


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
    issue = datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)
    assert issue['extra']['endpoint'] == SANITIZED_ENDPOINT
    datadog_agent.assert_reported_issue_count('openmetrics_test', 1)


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
    datadog_agent.assert_resolved_issue_count(1)
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
    EndpointUnreachableIssueReporter.report(
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

    datadog_agent.assert_resolved_issue(ISSUE_ID)
    datadog_agent.assert_resolved_issue_count(1)


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
    datadog_agent.assert_reported_issue_count('openmetrics_test', 1)


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
    EndpointUnreachableIssueReporter.report(
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

    datadog_agent.assert_resolved_issue(ISSUE_ID)
    datadog_agent.assert_resolved_issue_count(1)


def test_non_no_route_connection_error_does_not_report(datadog_agent):
    check, scraper_config = create_v1_check()
    error = requests.ConnectionError('connection refused', OSError(errno.ECONNREFUSED, 'Connection refused'))
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(scraper_config)

    assert exc_info.value is error
    datadog_agent.assert_no_reported_issues()


def test_v1_mixin_consumer_without_reporter_preserves_success_and_service_check():
    check = V1MixinConsumer()
    response = create_response(RAW_ENDPOINT)
    check.send_request = mock.Mock(return_value=response)

    assert check.poll(create_v1_scraper_config()) is response

    check.resolve_issue.assert_called_once_with(ISSUE_ID)
    check.service_check.assert_called_once_with(
        'demo.prometheus.health', AgentCheck.OK, tags=[f'endpoint:{RAW_ENDPOINT}']
    )


def test_v1_mixin_consumer_without_reporter_preserves_failure_and_service_check():
    check = V1MixinConsumer()
    error = unreachable_connection_error()
    check.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        check.poll(create_v1_scraper_config())

    assert exc_info.value is error
    assert check.report_issue.call_args.kwargs['id'] == ISSUE_ID
    check.service_check.assert_called_once_with(
        'demo.prometheus.health', AgentCheck.CRITICAL, tags=[f'endpoint:{RAW_ENDPOINT}']
    )


def test_v2_scraper_without_reporter_preserves_success_and_service_check(aggregator, datadog_agent):
    scraper, _ = create_v2_scraper_without_reporter()
    response = create_response(RAW_ENDPOINT)
    scraper.send_request = mock.Mock(return_value=response)

    assert scraper.get_connection() is response

    datadog_agent.assert_resolved_issue(ISSUE_ID)
    datadog_agent.assert_resolved_issue_count(1)
    aggregator.assert_service_check(
        'openmetrics.health',
        ServiceCheck.OK,
        tags=(f'endpoint:{RAW_ENDPOINT}',),
        count=1,
    )


def test_v2_scraper_without_reporter_preserves_failure_and_service_check(aggregator, datadog_agent):
    scraper, _ = create_v2_scraper_without_reporter()
    error = unreachable_connection_error()
    scraper.send_request = mock.Mock(side_effect=error)

    with pytest.raises(requests.ConnectionError) as exc_info:
        scraper.get_connection()

    assert exc_info.value is error
    datadog_agent.assert_reported_issue('openmetrics_test', ISSUE_ID)
    datadog_agent.assert_reported_issue_count('openmetrics_test', 1)
    aggregator.assert_service_check(
        'openmetrics.health',
        ServiceCheck.CRITICAL,
        tags=(f'endpoint:{RAW_ENDPOINT}',),
        count=1,
    )
