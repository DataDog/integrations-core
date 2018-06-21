# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from dns.resolver import Resolver, Timeout

from datadog_checks.dns_check import DNSCheck

import mock
from .mocks import MockTime, success_query_mock, nxdomain_query_mock


RESULTS_TIMEOUT = 10

CONFIG_SUCCESS = {
    'instances': [{
        'name': 'success',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1'
    }, {
        'name': 'cname',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1',
        'record_type': 'CNAME'
    }]
}

CONFIG_SUCCESS_NXDOMAIN = {
    'name': 'nxdomain',
    'hostname': 'www.example.org',
    'nameserver': '127.0.0.1',
    'record_type': 'NXDOMAIN'
}

CONFIG_DEFAULT_TIMEOUT = {
    'init_config': {
        'default_timeout': 0.1
    },
    'instances': [{
        'name': 'default_timeout',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1'
    }]
}

CONFIG_INSTANCE_TIMEOUT = {
    'name': 'instance_timeout',
    'hostname': 'www.example.org',
    'timeout': 0.1,
    'nameserver': '127.0.0.1'
}

CONFIG_INVALID = [
    # invalid hostname
    ({'name': 'invalid_hostname',
        'hostname': 'example'}, "DNS resolution of example has failed"),
    # invalid nameserver
    ({'name': 'invalid_nameserver',
        'hostname': 'www.example.org',
        'nameserver': '0.0.0.0'}, "DNS resolution of www.example.org timed out"),
    # invalid record type
    ({'name': 'invalid_rcrd_type',
        'hostname': 'www.example.org',
        'record_type': 'FOO'}, "DNS resolution of www.example.org has failed"),
    # valid domain when NXDOMAIN is expected
    ({'name': 'valid_domain_for_nxdomain_type',
        'hostname': 'example.com',
        'record_type': 'NXDOMAIN'}, "DNS resolution of example.com has failed"),
]


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
def test_success(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, {})

    integration.check(CONFIG_SUCCESS['instances'][0])
    tags = ['instance:success', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK,
                                    tags=tags, count=1)

    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    integration.check(CONFIG_SUCCESS['instances'][1])
    tags = ['instance:cname', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:CNAME']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK,
                                    tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=nxdomain_query_mock)
def test_success_nxdomain(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, {})
    integration.check(CONFIG_SUCCESS_NXDOMAIN)

    tags = ['instance:nxdomain', 'nameserver:127.0.0.1', 'resolved_hostname:www.example.org', 'record_type:NXDOMAIN']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK,
                                    tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=Timeout())
def test_default_timeout(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', CONFIG_DEFAULT_TIMEOUT['init_config'], {})
    integration.check(CONFIG_DEFAULT_TIMEOUT['instances'][0])

    tags = ['instance:default_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL,
                                    tags=tags, count=1, message="DNS resolution of www.example.org timed out")

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=Timeout())
def test_instance_timeout(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, {})
    integration.check(CONFIG_INSTANCE_TIMEOUT)

    tags = ['instance:instance_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL,
                                    tags=tags, count=1, message="DNS resolution of www.example.org timed out")

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def test_invalid_config(aggregator):
    integration = DNSCheck('dns_check', {}, {})
    for instance, message in CONFIG_INVALID:
        integration.check(instance)
        aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME,
                                        status=DNSCheck.CRITICAL,
                                        count=1,
                                        message=message)

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
