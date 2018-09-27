# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import mock

from datadog_checks.http_check import HTTPCheck
from datadog_checks.http_check.http_check import DEFAULT_EXPECTED_CODE
from datadog_checks.utils.headers import headers as agent_headers
from .common import (
    HERE, FAKE_CERT, CONFIG, CONFIG_SSL_ONLY, CONFIG_EXPIRED_SSL, CONFIG_CUSTOM_NAME,
    CONFIG_DATA_METHOD, CONFIG_HTTP_REDIRECTS, CONFIG_UNORMALIZED_INSTANCE_NAME,
    CONFIG_DONT_CHECK_EXP
)


@pytest.mark.unit
def test__init__():
    init_config = {
        'ca_certs': 'foo'
    }
    with mock.patch('datadog_checks.http_check.http_check.get_ca_certs_path'):
        http_check = HTTPCheck('http_check', init_config, {})
        assert http_check.ca_certs == 'foo'


@pytest.mark.unit
def test__load_conf(http_check):
    """
    Test the defaults and the pieces of _load_conf that actually perform some logic
    """
    # misconfiguration
    with pytest.raises(Exception) as e:
        http_check._load_conf({})
        assert 'Bad configuration' in str(e)

    # defaults
    params = http_check._load_conf({
        'url': 'https://example.com',
        'name': 'UpService',
    })
    assert len(params) == 24

    # `url` is mandatory
    assert params[0] == 'https://example.com'
    # default `ntlm_domain` is None
    assert params[1] is None
    # default `username` is None
    assert params[2] is None
    # default `password` is None
    assert params[3] is None
    # defualt `client_cert` is None
    assert params[4] is None
    # defualt `client_key` is None
    assert params[5] is None
    # default `method` is get
    assert params[6] == 'get'
    # default `data` is an empty dict
    assert params[7] == {}
    # default `http_response_status_code`
    assert params[8] == DEFAULT_EXPECTED_CODE
    # default `timeout` is 10
    assert params[9] == 10
    # default `include_content` is False
    assert params[10] is False
    # default headers
    assert params[11] == agent_headers({})
    # default `collect_response_time` is True
    assert params[12] is True
    # default `content_match` is None
    assert params[13] is None
    # default `reverse_content_match` is False
    assert params[14] is False
    # default `tags` is an empty list
    assert params[15] == []
    # default `disable_ssl_validation` is True
    assert params[16] is True
    # default `check_certificate_expiration` is True
    assert params[17] is True
    # default `ca_certs`, it's mocked we don't care
    assert params[18] != ''
    # default `weakciphers` is False
    assert params[19] is False
    # default `check_hostname` is True
    assert params[20] is True
    # default `ignore_ssl_warning` is False
    assert params[21] is False
    # default `skip_proxy` is False
    assert params[22] is False
    # default `allow_redirects` is True
    assert params[23] is True

    # headers
    params = http_check._load_conf({
        'url': 'https://example.com',
        'name': 'UpService',
        'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}
    })

    headers = params[11]
    expected_headers = agent_headers({}).get('User-Agent')
    assert headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers
    assert expected_headers == headers.get('User-Agent'), headers

    # proxy
    params = http_check._load_conf({
        'url': 'https://example.com',
        'name': 'UpService',
        'no_proxy': True,
    })
    assert params[22] is True

    params = http_check._load_conf({
        'url': 'https://example.com',
        'name': 'UpService',
        'no_proxy': False,
        'skip_proxy': True,
    })
    assert params[22] is True


@pytest.mark.unit
def test_check_cert_expiration(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    check_hostname = True

    # up
    instance = {
        'url': 'https://sha256.badssl.com/'
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'UP'
    assert days_left > 0
    assert seconds_left > 0

    # bad hostname
    instance = {
        'url': 'https://wrong.host.badssl.com/'
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'CRITICAL'
    assert days_left == 0
    assert seconds_left == 0
    assert msg == "hostname 'wrong.host.badssl.com' doesn't match either of '*.badssl.com', 'badssl.com'"

    # site is down
    instance = {
        'url': 'https://this.does.not.exist.foo'
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'DOWN'
    assert days_left == 0
    assert seconds_left == 0

    # cert expired
    instance = {
        'url': 'https://expired.badssl.com/'
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'DOWN'
    assert days_left == 0
    assert seconds_left == 0

    # critical in days
    days_critical = 1000
    instance = {
        'url': 'https://sha256.badssl.com/',
        'days_critical': days_critical,
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'CRITICAL'
    assert 0 < days_left < days_critical

    # critical in seconds (ensure seconds take precedence over days config)
    seconds_critical = days_critical * 24 * 3600
    instance = {
        'url': 'https://sha256.badssl.com/',
        'days_critical': 0,
        'seconds_critical': seconds_critical,
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'CRITICAL'
    assert 0 < seconds_left < seconds_critical

    # warning in days
    days_warning = 1000
    instance = {
        'url': 'https://sha256.badssl.com/',
        'days_warning': days_warning,
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'WARNING'
    assert 0 < days_left < days_warning

    # warning in seconds (ensure seconds take precedence over days config)
    seconds_warning = days_warning * 24 * 3600
    instance = {
        'url': 'https://sha256.badssl.com/',
        'days_warning': 0,
        'seconds_warning': seconds_warning,
    }
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == 'WARNING'
    assert 0 < seconds_left < seconds_warning


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

    # Run the check for the one instance configured with days left
    http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://github.com', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


@mock.patch('ssl.SSLSocket.getpeercert', **{'return_value.raiseError.side_effect': Exception()})
def test_check_ssl_expire_error_secs(getpeercert_func, aggregator, http_check):

    # Run the check for the one instance configured with seconds left
    http_check.check(CONFIG_EXPIRED_SSL['instances'][1])

    expired_cert_tags = ['url:https://github.com', 'instance:expired_cert_seconds']
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
