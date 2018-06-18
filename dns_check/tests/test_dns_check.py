# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from .mocks import MockTime, success_query_mock, nxdomain_query_mock
# stdlib
import mock

# 3p
from dns.rdatatype import UnknownRdatatype
from dns.resolver import Resolver, Timeout, NXDOMAIN

# project
from datadog_checks.dns_check import DNSCheck

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
    'instances': [{
        'name': 'nxdomain',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1',
        'record_type': 'NXDOMAIN'
    }]
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
    'instances': [{
        'name': 'instance_timeout',
        'hostname': 'www.example.org',
        'timeout': 0.1,
        'nameserver': '127.0.0.1'
    }]
}

CONFIG_INVALID = [
    # invalid hostname
    ({'instances': [{
        'name': 'invalid_hostname',
        'hostname': 'example'}]}, NXDOMAIN),
    # invalid nameserver
    ({'instances': [{
        'name': 'invalid_nameserver',
        'hostname': 'www.example.org',
        'nameserver': '0.0.0.0'}]}, Timeout),
    # invalid record type
    ({'instances': [{
        'name': 'invalid_rcrd_type',
        'hostname': 'www.example.org',
        'record_type': 'FOO'}]}, UnknownRdatatype),
    # valid domain when NXDOMAIN is expected
    ({'instances': [{
        'name': 'valid_domain_for_nxdomain_type',
        'hostname': 'example.com',
        'record_type': 'NXDOMAIN'}]}, AssertionError),
]


@mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
@mock.patch('time.time', side_effect=MockTime.time)
def test_success(mocked_query, mocked_time, aggregator):
    dns_check = DNSCheck('dns_check', {}, {})
    dns_check.check(CONFIG_SUCCESS)

    tags = ['instance:success', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, value=1, count=1)
    tags = ['instance:cname', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:CNAME']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, value=1, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.reset()


@mock.patch.object(Resolver, 'query', side_effect=nxdomain_query_mock)
@mock.patch('time.time', side_effect=MockTime.time)
def test_success_nxdomain(mocked_query, mocked_time, aggregator):
    dns_check = DNSCheck('dns_check', {}, {})
    dns_check.check(CONFIG_SUCCESS_NXDOMAIN)

    tags = ['instance:nxdomain', 'nameserver:127.0.0.1', 'resolved_hostname:www.example.org', 'record_type:NXDOMAIN']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, value=1, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.reset()


@mock.patch.object(Resolver, 'query', side_effect=Timeout())
@mock.patch('time.time', side_effect=MockTime.time)
def test_default_timeout(mocked_query, mocked_time, aggregator):
    dns_check = DNSCheck('dns_check', {}, {})
    dns_check.check(CONFIG_DEFAULT_TIMEOUT)

    tags = ['instance:default_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, tags=tags, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.reset()


@mock.patch.object(Resolver, 'query', side_effect=Timeout())
@mock.patch('time.time', side_effect=MockTime.time)
def test_instance_timeout(mocked_query, mocked_time, aggregator):
    dns_check = DNSCheck('dns_check', {}, {})
    dns_check.check(CONFIG_INSTANCE_TIMEOUT)

    tags = ['instance:instance_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, tags=tags, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()
    aggregator.reset()


def test_invalid_config(aggregator):
    for config, exception_class in CONFIG_INVALID:
        dns_check = DNSCheck('dns_check', {}, {})
        try:
            dns_check.check(config)
        except Exception:
            pass
        else:
            assert False, "Should have thrown an exception due to invalid configuration"

        aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, count=1)

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
        aggregator.reset()
