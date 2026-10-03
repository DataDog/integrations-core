# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from dns.resolver import Resolver

from datadog_checks.dns_check import DNSCheck

from . import common
from .mocks import MockDNSAnswer, MockTime, nxdomain_query_mock, success_query_mock

pytestmark = pytest.mark.unit


def test_default_timeout_falls_back_to_class_constant():
    instance = {"name": "no_timeout", "hostname": "www.example.org", "nameserver": "127.0.0.1"}
    integration = DNSCheck("dns_check", {}, [instance])
    assert integration.timeout == 5.0


def test_init_defaults_the_name_of_the_first_instance():
    first = {"hostname": "first.example.org", "nameserver": "127.0.0.1"}
    second = {"name": "second", "hostname": "second.example.org", "nameserver": "127.0.0.1"}
    integration = DNSCheck("dns_check", {}, [first, second])
    assert "instance:dns-check-0" in integration.base_tags


def test_base_tags_include_resolved_as_when_configured():
    instance = {"name": "ras", "hostname": "www.example.org", "nameserver": "127.0.0.1", "resolves_as": "127.0.0.2"}
    integration = DNSCheck("dns_check", {}, [instance])
    assert "resolved_as:127.0.0.2" in integration.base_tags


def test_get_resolver_uses_the_configured_nameserver():
    instance = {"name": "ns", "hostname": "www.example.org", "nameserver": "9.9.9.9"}
    integration = DNSCheck("dns_check", {}, [instance])
    resolver = integration._get_resolver()
    assert resolver.nameservers == ["9.9.9.9"]


def test_get_resolver_uses_the_configured_nameserver_port():
    instance = {"name": "ns_port", "hostname": "www.example.org", "nameserver": "9.9.9.9", "nameserver_port": 5353}
    integration = DNSCheck("dns_check", {}, [instance])
    resolver = integration._get_resolver()
    assert resolver.port == 5353


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", side_effect=nxdomain_query_mock)
def test_record_type_equal_to_nxdomain_queries_without_rdtype(mocked_query, mocked_time):
    record_type = "".join(["NX", "DOMAIN"])
    instance = {"name": "nx", "hostname": "www.example.org", "nameserver": "127.0.0.1", "record_type": record_type}
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    mocked_query.assert_called_once_with(integration.hostname)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", return_value=MockDNSAnswer("1.2.3.4"))
def test_record_type_greater_than_nxdomain_queries_with_rdtype(mocked_query, mocked_time, aggregator):
    instance = {"name": "txt", "hostname": "www.example.org", "nameserver": "127.0.0.1", "record_type": "TXT"}
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    mocked_query.assert_called_once_with(integration.hostname, rdtype="TXT")
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=[7, 20])
@mock.patch.object(Resolver, "query", side_effect=nxdomain_query_mock)
def test_nxdomain_response_time_is_a_subtraction(mocked_query, mocked_time, aggregator):
    integration = DNSCheck("dns_check", {}, [common.CONFIG_SUCCESS_NXDOMAIN])
    integration.check(common.CONFIG_SUCCESS_NXDOMAIN)
    aggregator.assert_metric("dns.response_time", value=13, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=[7, 20])
@mock.patch.object(Resolver, "query", side_effect=success_query_mock)
def test_success_response_time_is_a_subtraction(mocked_query, mocked_time, aggregator):
    instance = common.CONFIG_SUCCESS["instances"][0]
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_metric("dns.response_time", value=13, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=[5, 5])
@mock.patch.object(Resolver, "query", side_effect=success_query_mock)
def test_zero_response_time_is_not_reported(mocked_query, mocked_time, aggregator):
    instance = common.CONFIG_SUCCESS["instances"][0]
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_metric("dns.response_time", count=0)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=[20, 7])
@mock.patch.object(Resolver, "query", side_effect=success_query_mock)
def test_negative_response_time_is_not_reported(mocked_query, mocked_time, aggregator):
    instance = common.CONFIG_SUCCESS["instances"][0]
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_metric("dns.response_time", count=0)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=[10, 11])
@mock.patch.object(Resolver, "query", side_effect=success_query_mock)
def test_response_time_of_one_is_reported(mocked_query, mocked_time, aggregator):
    instance = common.CONFIG_SUCCESS["instances"][0]
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_metric("dns.response_time", value=1, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", return_value=MockDNSAnswer("127.0.0.2,127.0.0.3"))
def test_resolves_as_count_mismatch_fails_when_fewer_expected(mocked_query, mocked_time, aggregator):
    instance = {"name": "fewer", "hostname": "www.example.org", "nameserver": "127.0.0.1", "resolves_as": "127.0.0.2"}
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", return_value=MockDNSAnswer("127.0.0.2"))
def test_resolves_as_count_mismatch_fails_when_more_expected(mocked_query, mocked_time, aggregator):
    instance = {
        "name": "more",
        "hostname": "www.example.org",
        "nameserver": "127.0.0.1",
        "resolves_as": "127.0.0.2,127.0.0.2",
    }
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
def test_resolves_as_count_equal_but_not_the_same_int_object_still_matches(mocked_time, aggregator):
    addresses = ["ip{}".format(i) for i in range(300)]
    resolves_as = ",".join(addresses)
    instance = {
        "name": "many",
        "hostname": "www.example.org",
        "nameserver": "127.0.0.1",
        "resolves_as": resolves_as,
    }
    with mock.patch.object(Resolver, "query", return_value=MockDNSAnswer(resolves_as)):
        integration = DNSCheck("dns_check", {}, [instance])
        integration.check(instance)
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", return_value=MockDNSAnswer("alias.example.org."))
def test_check_answer_strips_trailing_dot(mocked_query, mocked_time, aggregator):
    instance = {
        "name": "trailing_dot",
        "hostname": "www.example.org",
        "nameserver": "127.0.0.1",
        "record_type": "CNAME",
        "resolves_as": "alias.example.org",
    }
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.OK, count=1)


@mock.patch("datadog_checks.dns_check.dns_check.get_precise_time", side_effect=MockTime.time)
@mock.patch.object(Resolver, "query", return_value=MockDNSAnswer("127.0.0.3"))
def test_resolves_as_mismatched_ip_is_reported_as_critical(mocked_query, mocked_time, aggregator):
    instance = {
        "name": "mismatch_ip",
        "hostname": "www.example.org",
        "nameserver": "127.0.0.1",
        "resolves_as": "127.0.0.2",
    }
    integration = DNSCheck("dns_check", {}, [instance])
    integration.check(instance)
    aggregator.assert_service_check(DNSCheck.SERVICE_CHECK_NAME, status=DNSCheck.CRITICAL, count=1)


def test_get_tags_uses_first_system_nameserver():
    instance = {"name": "no_nameserver", "hostname": "www.example.org"}
    integration = DNSCheck("dns_check", {}, [instance])
    with mock.patch("datadog_checks.dns_check.dns_check.dns.resolver.Resolver") as mock_resolver_cls:
        mock_resolver_cls.return_value.nameservers = ["9.9.9.9", "1.1.1.1", "8.8.8.8"]
        tags = integration._get_tags()
    assert "nameserver:9.9.9.9" in tags


def test_get_tags_handles_no_system_nameserver():
    instance = {"name": "no_nameserver", "hostname": "www.example.org"}
    integration = DNSCheck("dns_check", {}, [instance])
    with mock.patch("datadog_checks.dns_check.dns_check.dns.resolver.Resolver") as mock_resolver_cls:
        mock_resolver_cls.return_value.nameservers = []
        tags = integration._get_tags()
    assert "nameserver:" in tags
