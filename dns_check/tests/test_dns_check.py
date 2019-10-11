# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
from dns.resolver import Resolver, Timeout

from datadog_checks.dns_check import DNSCheck

from . import common
from .mocks import MockTime, nxdomain_query_mock, success_query_mock

RESULTS_TIMEOUT = 10


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
def test_success(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, common.CONFIG_SUCCESS['instances'])

    integration.check(common.CONFIG_SUCCESS['instances'][0])
    tags = ['instance:success', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    integration.check(common.CONFIG_SUCCESS['instances'][2])
    tags = [
        'instance:check_response_ip',
        'resolved_hostname:www.example.org',
        'nameserver:127.0.0.1',
        'record_type:A',
        'resolved_as:127.0.0.2',
    ]
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    integration.check(common.CONFIG_SUCCESS['instances'][3])
    tags = [
        'instance:check_response_multiple_ips',
        'resolved_hostname:my.example.org',
        'nameserver:127.0.0.1',
        'record_type:A',
        'resolved_as:127.0.0.2,127.0.0.3,127.0.0.4',
    ]
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    integration.check(common.CONFIG_SUCCESS['instances'][4])
    tags = [
        'instance:check_response_CNAME',
        'resolved_hostname:www.example.org',
        'nameserver:127.0.0.1',
        'record_type:CNAME',
        'resolved_as:alias.example.org',
    ]
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    integration.check(common.CONFIG_SUCCESS['instances'][1])
    tags = ['instance:cname', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:CNAME']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=nxdomain_query_mock)
def test_success_nxdomain(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, [common.CONFIG_SUCCESS_NXDOMAIN])
    integration.check(common.CONFIG_SUCCESS_NXDOMAIN)

    tags = ['instance:nxdomain', 'nameserver:127.0.0.1', 'resolved_hostname:www.example.org', 'record_type:NXDOMAIN']
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, tags=tags, count=1)
    aggregator.assert_metric('dns.response_time', tags=tags, count=1, value=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=Timeout())
def test_default_timeout(mocked_query, mocked_time, aggregator):
    integration = DNSCheck(
        'dns_check', common.CONFIG_DEFAULT_TIMEOUT['init_config'], common.CONFIG_DEFAULT_TIMEOUT['instances']
    )
    integration.check(common.CONFIG_DEFAULT_TIMEOUT['instances'][0])

    tags = ['instance:default_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(
        DNSCheck.SERVICE_CHECK_NAME,
        status=DNSCheck.CRITICAL,
        tags=tags,
        count=1,
        message="DNS resolution of www.example.org timed out",
    )

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


@mock.patch('datadog_checks.dns_check.dns_check.time_func', side_effect=MockTime.time)
@mock.patch.object(Resolver, 'query', side_effect=Timeout())
def test_instance_timeout(mocked_query, mocked_time, aggregator):
    integration = DNSCheck('dns_check', {}, [common.CONFIG_INSTANCE_TIMEOUT])
    integration.check(common.CONFIG_INSTANCE_TIMEOUT)

    tags = ['instance:instance_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
    aggregator.assert_service_check(
        DNSCheck.SERVICE_CHECK_NAME,
        status=DNSCheck.CRITICAL,
        tags=tags,
        count=1,
        message="DNS resolution of www.example.org timed out",
    )

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def test_invalid_config(aggregator):
    for instance, message in common.CONFIG_INVALID:
        integration = DNSCheck('dns_check', {}, [instance])
        integration.check(instance)
        aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, count=1, message=message)

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
