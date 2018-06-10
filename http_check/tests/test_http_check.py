# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# 3p
import mock

from datadog_checks.http_check import HTTPCheck
from datadog_checks.utils.headers import headers as agent_headers
from .common import (
    FAKE_CERT, CONFIG, CONFIG_HTTP_HEADERS, CONFIG_SSL_ONLY, CONFIG_EXPIRED_SSL, CONFIG_CUSTOM_NAME, CONFIG_DATA_METHOD,
    CONFIG_HTTP_REDIRECTS, CONFIG_UNORMALIZED_INSTANCE_NAME, CONFIG_DONT_CHECK_EXP
)


def test_http_headers(http_check):
    """
    Headers format.
    """

    # Get just the headers from http_check._load_conf(...), which happens to be at index 10
    headers = http_check._load_conf(CONFIG_HTTP_HEADERS['instances'][0])[10]

    expected_headers = agent_headers({}).get('User-Agent')

    assert headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers
    assert expected_headers == headers.get('User-Agent'), headers


def test_check(aggregator, http_check):
    """
    Check coverage.
    """

    # Run the check for all the instances in the config
    for instance in CONFIG['instances']:
        http_check.check(instance)

    # HTTP connection error
    connection_err_tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)

    # Wrong HTTP response status code
    status_code_err_tags = ['url:http://httpbin.org/404', 'instance:http_error_status_code']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=status_code_err_tags, count=1)

    # HTTP response status code match
    status_code_match_tags = ['url:http://httpbin.org/404', 'instance:status_code_match', 'foo:bar']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=status_code_match_tags, count=1)

    # Content match & mismatching
    content_match_tags = ['url:https://github.com', 'instance:cnt_match']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=content_match_tags, count=1)

    content_mismatch_tags = ['url:https://github.com', 'instance:cnt_mismatch']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=content_mismatch_tags, count=1)

    unicode_content_match_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_match_unicode']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=unicode_content_match_tags, count=1)

    unicode_content_mismatch_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_mismatch_unicode']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=unicode_content_mismatch_tags,
                                    count=1)

    reverse_content_match_tags = ['url:https://github.com', 'instance:cnt_match_reverse']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=reverse_content_match_tags,
                                    count=1)

    reverse_content_mismatch_tags = ['url:https://github.com', 'instance:cnt_mismatch_reverse']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=reverse_content_mismatch_tags,
                                    count=1)

    unicode_reverse_content_match_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_match_unicode_reverse']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL,
                                    tags=unicode_reverse_content_match_tags, count=1)

    unicode_reverse_content_mismatch_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_mismatch_unicode_reverse']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK,
                                    tags=unicode_reverse_content_mismatch_tags, count=1)


def test_check_ssl(aggregator, http_check):

    # Run the check for all the instances in the config
    for instance in CONFIG_SSL_ONLY['instances']:
        http_check.check(instance)

    good_cert_tags = ['url:https://github.com:443', 'instance:good_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=good_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=good_cert_tags, count=1)

    expiring_soon_cert_tags = ['url:https://google.com', 'instance:cert_exp_soon']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expiring_soon_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.WARNING, tags=expiring_soon_cert_tags,
                                    count=1)

    critical_cert_tags = ['url:https://google.com', 'instance:cert_critical']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=critical_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=critical_cert_tags, count=1)

    connection_err_tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)


@mock.patch('ssl.SSLSocket.getpeercert', **{'return_value.raiseError.side_effect': Exception()})
def test_check_ssl_expire_error(getpeercert_func, aggregator, http_check):

    # Run the check for the one instance
    http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://github.com', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


def test_check_hostname_override(aggregator, http_check):

    # Run the check for all the instances in the config
    for instance in CONFIG_CUSTOM_NAME['instances']:
        http_check.check(instance)

    cert_validation_fail_tags = ['url:https://github.com:443', 'instance:cert_validation_fails']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_fail_tags,
                                    count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=cert_validation_fail_tags,
                                    count=1)

    cert_validation_pass_tags = ['url:https://github.com:443', 'instance:cert_validation_passes']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_pass_tags,
                                    count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=cert_validation_pass_tags,
                                    count=1)


def test_check_allow_redirects(aggregator, http_check):

    # Run the check for the one instance
    http_check.check(CONFIG_HTTP_REDIRECTS['instances'][0])

    redirect_service_tags = ['url:http://github.com', 'instance:redirect_service']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK,
                                    tags=redirect_service_tags, count=1)


@mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT)
def test_mock_case(getpeercert_func, aggregator, http_check):

    # Run the check for the one instance
    http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://github.com', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


def test_service_check_instance_name_normalization(aggregator, http_check):
    """
    Service check `instance` tag value is normalized.

    Note: necessary to avoid mismatch and backward incompatiblity.
    """

    # Run the check for the one instance
    http_check.check(CONFIG_UNORMALIZED_INSTANCE_NAME['instances'][0])

    # Assess instance name normalization
    normalized_tags = ['url:https://github.com', 'instance:need_to_be_normalized']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=normalized_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=normalized_tags, count=1)


def test_dont_check_expiration(aggregator, http_check):

    # Run the check for the one instance
    instance = CONFIG_DONT_CHECK_EXP['instances'][0]
    http_check.check(instance)

    url_tag = ['url:{}'.format(instance.get('url'))]
    instance_tag = ['instance:{}'.format(instance.get('name'))]

    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=url_tag + instance_tag, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, tags=url_tag + instance_tag, count=0)


def test_data_methods(aggregator, http_check):

    # Run the check once for both POST configs
    for instance in CONFIG_DATA_METHOD['instances']:
        http_check.check(instance)

        url_tag = ['url:{}'.format(instance.get('url'))]
        instance_tag = ['instance:{}'.format(instance.get('name'))]

        aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=url_tag + instance_tag, count=1)
        aggregator.assert_metric('network.http.can_connect', tags=url_tag, value=1, count=1)
        aggregator.assert_metric('network.http.cant_connect', tags=url_tag, value=0, count=1)
        aggregator.assert_metric('network.http.response_time', tags=url_tag, count=1)

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
        aggregator.reset()
