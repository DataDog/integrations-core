# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import os
import pytest

import ldap3

from datadog_checks.errors import CheckException
from .common import HERE


def test_check(check, aggregator, mocker):
    server_mock = ldap3.Server("fake_server")
    conn_mock = ldap3.Connection(server_mock, client_strategy=ldap3.MOCK_SYNC, collect_usage=True)
    # usage.last_received_time is not populated when using mock connection, let's set a value
    conn_mock.usage.last_received_time = datetime.datetime.now()
    conn_mock.strategy.entries_from_json(os.path.join(HERE, "fixtures", "monitor.json"))
    instance = {
        "url": "fake_server",
        "custom_queries": [{
            "name": "stats",
            "search_base": "cn=statistics,cn=monitor",
            "search_filter": "(!(cn=Statistics))",
        }]
    }

    mocker.patch("datadog_checks.openldap.openldap.ldap3.Server", return_value=server_mock)
    mocker.patch("datadog_checks.openldap.openldap.ldap3.Connection", return_value=conn_mock)
    check.check(instance)
    tags = ["url:fake_server"]
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)
    aggregator.assert_metric("openldap.bind_time", tags=tags)
    aggregator.assert_metric("openldap.connections.current", 1, tags=tags)
    aggregator.assert_metric("openldap.connections.max_file_descriptors", 1024, tags=tags)
    aggregator.assert_metric("openldap.connections.total", 3453, tags=tags)
    aggregator.assert_metric("openldap.operations.completed.total", 41398, tags=tags)
    aggregator.assert_metric("openldap.operations.initiated.total", 41399, tags=tags)
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:abandon"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:abandon"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:add"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:add"])
    aggregator.assert_metric("openldap.operations.completed", 9734, tags=tags + ["operation:bind"])
    aggregator.assert_metric("openldap.operations.initiated", 9734, tags=tags + ["operation:bind"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:compare"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:compare"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:delete"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:delete"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:extended"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:extended"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:modify"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:modify"])
    aggregator.assert_metric("openldap.operations.completed", 0, tags=tags + ["operation:modrdn"])
    aggregator.assert_metric("openldap.operations.initiated", 0, tags=tags + ["operation:modrdn"])
    aggregator.assert_metric("openldap.operations.completed", 29212, tags=tags + ["operation:search"])
    aggregator.assert_metric("openldap.operations.initiated", 29213, tags=tags + ["operation:search"])
    aggregator.assert_metric("openldap.operations.completed", 2452, tags=tags + ["operation:unbind"])
    aggregator.assert_metric("openldap.operations.initiated", 2452, tags=tags + ["operation:unbind"])
    aggregator.assert_metric("openldap.statistics.bytes", 796449497, tags=tags)
    aggregator.assert_metric("openldap.statistics.entries", 178382, tags=tags)
    aggregator.assert_metric("openldap.statistics.pdu", 217327, tags=tags)
    aggregator.assert_metric("openldap.statistics.referrals", 0, tags=tags)
    aggregator.assert_metric("openldap.threads", 1, tags=tags + ["status:active"])
    aggregator.assert_metric("openldap.threads", 1, tags=tags + ["status:backload"])
    aggregator.assert_metric("openldap.threads", 3, tags=tags + ["status:open"])
    aggregator.assert_metric("openldap.threads", 0, tags=tags + ["status:pending"])
    aggregator.assert_metric("openldap.threads", 0, tags=tags + ["status:starting"])
    aggregator.assert_metric("openldap.threads.max", 16, tags=tags)
    aggregator.assert_metric("openldap.threads.max_pending", 0, tags=tags)
    aggregator.assert_metric("openldap.uptime", 159182, tags=tags)
    aggregator.assert_metric("openldap.waiter.read", 1, tags=tags)
    aggregator.assert_metric("openldap.waiter.write", 0, tags=tags)
    aggregator.assert_metric("openldap.query.duration", tags=tags + ["query:stats"])
    aggregator.assert_metric("openldap.query.entries", 4, tags=tags + ["query:stats"])
    aggregator.assert_all_metrics_covered()


def test__get_tls_object(check, mocker):
    os_mock = mocker.patch("datadog_checks.openldap.openldap.os")
    ldap3_tls_mock = mocker.patch("datadog_checks.openldap.openldap.ldap3.core.tls.Tls")
    ssl_mock = mocker.patch("datadog_checks.openldap.openldap.ssl")

    # Check no SSL
    assert check._get_tls_object(None) is None

    # Check emission of warning, ssl validation none, and ca_certs_file
    ssl_params = {
        "key": None,
        "cert": None,
        "ca_certs": "foo",
        "verify": False,
    }
    os_mock.path.isdir.return_value = False
    os_mock.path.isfile.return_value = True
    log_mock = mocker.MagicMock()
    check.log = log_mock
    check._get_tls_object(ssl_params)
    log_mock.warning.assert_called_once()
    assert "Incorrect configuration" in log_mock.warning.call_args[0][0]
    ldap3_tls_mock.assert_called_once_with(
        local_private_key_file=None,
        local_certificate_file=None,
        validate=ssl_mock.CERT_NONE,
        version=ssl_mock.PROTOCOL_SSLv23,
        ca_certs_file="foo",
    )

    # Check no warning, ssl validation required, and ca_certs_file none
    log_mock.reset_mock()
    ldap3_tls_mock.reset_mock()
    ssl_params = {
        "key": "foo",
        "cert": "bar",
        "ca_certs": None,
        "verify": True,
    }
    check._get_tls_object(ssl_params)
    log_mock.warning.assert_not_called()
    ldap3_tls_mock.assert_called_once_with(
        local_private_key_file="foo",
        local_certificate_file="bar",
        validate=ssl_mock.CERT_REQUIRED,
        version=ssl_mock.PROTOCOL_SSLv23,
        ca_certs_file=None,
    )

    # Check ca_certs_path
    os_mock.path.isdir.return_value = True
    os_mock.path.isfile.return_value = False
    ldap3_tls_mock.reset_mock()
    ssl_params = {
        "key": "foo",
        "cert": "bar",
        "ca_certs": "foo",
        "verify": True,
    }
    check._get_tls_object(ssl_params)
    ldap3_tls_mock.assert_called_once_with(
        local_private_key_file="foo",
        local_certificate_file="bar",
        validate=ssl_mock.CERT_REQUIRED,
        version=ssl_mock.PROTOCOL_SSLv23,
        ca_certs_path="foo",
    )

    # Check exception when invalid ca_certs_path
    with pytest.raises(CheckException):
        os_mock.path.isdir.return_value = False
        os_mock.path.isfile.return_value = False
        ssl_params = {
            "key": "foo",
            "cert": "bar",
            "ca_certs": "foo",
            "verify": True,
        }
        check._get_tls_object(ssl_params)


def test__get_instance_params(check):
    # Check default values
    instance = {
        "url": "foo",
    }
    assert check._get_instance_params(instance) == ("foo", None, None, None, [], ["url:foo"])

    # Check instance with no url raises
    with pytest.raises(CheckException):
        check._get_instance_params({})

    # Check ssl_params is None with non ldaps scheme
    instance = {
        "url": "ldap://foo",
        "ssl_key": "bar",
        "ssl_cert": "baz",
    }
    assert check._get_instance_params(instance) == ("ldap://foo", None, None, None, [], ["url:ldap://foo"])

    # Check all params ok
    url = "ldaps://url"
    user = "user"
    password = "pass"
    key = "key"
    cert = "cert"
    ca_certs = "capath"
    verify = False
    queries = ["query1", "query2"]
    tags = ["custom:tag"]
    ssl_params = {
        "key": key,
        "cert": cert,
        "ca_certs": ca_certs,
        "verify": verify,
    }
    instance = {
        "url": url,
        "username": user,
        "password": password,
        "ssl_key": key,
        "ssl_cert": cert,
        "ssl_ca_certs": ca_certs,
        "ssl_verify": verify,
        "custom_queries": queries,
        "tags": tags,
    }
    assert check._get_instance_params(instance) == (url, user, password, ssl_params,
                                                    queries, tags + ["url:ldaps://url"])

    # Check ssl_params default values
    url = "ldaps://url"
    ssl_params = {
        "key": None,
        "cert": None,
        "ca_certs": None,
        "verify": True,
    }
    instance = {
        "url": url,
    }
    assert check._get_instance_params(instance) == (url, None, None, ssl_params, [], ["url:ldaps://url"])


def test__perform_custom_queries(check, mocker):
    # Check name mandatory
    instance = {
        "url": "foo",
        "custom_queries": [{}]
    }
    log_mock = mocker.MagicMock()
    check.log = log_mock
    conn_mock = mocker.MagicMock()
    _, _, _, _, queries, tags = check._get_instance_params(instance)
    check._perform_custom_queries(conn_mock, queries, tags, instance)
    conn_mock.search.assert_not_called()  # No search performed
    log_mock.error.assert_called_once()  # Error logged

    # Check search_base mandatory
    instance = {
        "url": "foo",
        "custom_queries": [{"name": "foo"}]
    }
    log_mock.reset_mock()
    _, _, _, _, queries, tags = check._get_instance_params(instance)
    check._perform_custom_queries(conn_mock, queries, tags, instance)
    conn_mock.search.assert_not_called()  # No search performed
    log_mock.error.assert_called_once()  # Error logged

    # Check search_filter mandatory
    instance = {
        "url": "foo",
        "custom_queries": [{"name": "foo", "search_base": "bar"}]
    }
    log_mock.reset_mock()
    _, _, _, _, queries, tags = check._get_instance_params(instance)
    check._perform_custom_queries(conn_mock, queries, tags, instance)
    conn_mock.search.assert_not_called()  # No search performed
    log_mock.error.assert_called_once()  # Error logged

    # Check query rebind same username
    instance = {
        "url": "url",
        "username": "user",
        "password": "pass",
        "custom_queries": [{"name": "name", "search_base": "base", "search_filter": "filter"}]
    }
    log_mock.reset_mock()
    _, _, _, _, queries, tags = check._get_instance_params(instance)
    check._perform_custom_queries(conn_mock, queries, tags, instance)
    conn_mock.rebind.assert_called_once_with(user="user", password="pass", authentication=ldap3.SIMPLE)
    conn_mock.search.assert_called_once_with("base", "filter", attributes=None)
    log_mock.error.assert_not_called()  # No error logged

    # Check query rebind different user
    instance = {
        "url": "url",
        "username": "user",
        "password": "pass",
        "custom_queries": [{
            "name": "name", "search_base": "base", "search_filter": "filter",
            "username": "user2", "password": "pass2", "attributes": ["*"]
        }]
    }
    conn_mock.reset_mock()
    _, _, _, _, queries, tags = check._get_instance_params(instance)
    check._perform_custom_queries(conn_mock, queries, tags, instance)
    conn_mock.rebind.assert_called_once_with(user="user2", password="pass2", authentication=ldap3.SIMPLE)
    conn_mock.search.assert_called_once_with("base", "filter", attributes=["*"])
    log_mock.error.assert_not_called()  # No error logged


def test__extract_common_name(check):
    # Check lower case and spaces converted
    dn = "cn=Max File Descriptors,cn=Connections,cn=Monitor"
    assert check._extract_common_name(dn) == "max_file_descriptors"

    # Check one cn
    dn = "cn=Max File Descriptors"
    assert check._extract_common_name(dn) == "max_file_descriptors"
