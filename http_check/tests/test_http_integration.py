# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.http_check import HTTPCheck

from .common import (
    CONFIG_CUSTOM_NAME,
    CONFIG_DATA_METHOD,
    CONFIG_DONT_CHECK_EXP,
    CONFIG_EXPIRED_SSL,
    CONFIG_HTTP_REDIRECTS,
    CONFIG_SSL_ONLY,
    CONFIG_UNORMALIZED_INSTANCE_NAME,
    FAKE_CERT,
    HERE,
)


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    check_hostname = True

    # up
    instance = {'url': 'https://valid.mock/'}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.OK
    assert days_left > 0
    assert seconds_left > 0

    # bad hostname
    instance = {'url': 'https://wronghost.mock/'}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.CRITICAL
    assert days_left == 0
    assert seconds_left == 0
    assert 'Hostname mismatch' in msg or "doesn't match" in msg

    # site is down
    instance = {'url': 'https://this.does.not.exist.foo'}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.CRITICAL
    assert days_left == 0
    assert seconds_left == 0

    # cert expired
    instance = {'url': 'https://expired.mock/'}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.CRITICAL
    assert days_left == 0
    assert seconds_left == 0

    # critical in days
    days_critical = 200
    instance = {'url': 'https://valid.mock/', 'days_critical': days_critical}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.CRITICAL
    assert 0 < days_left < days_critical

    # critical in seconds (ensure seconds take precedence over days config)
    seconds_critical = days_critical * 24 * 3600
    instance = {'url': 'https://valid.mock/', 'days_critical': 0, 'seconds_critical': seconds_critical}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.CRITICAL
    assert 0 < seconds_left < seconds_critical

    # warning in days
    days_warning = 200
    instance = {'url': 'https://valid.mock/', 'days_warning': days_warning}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.WARNING
    assert 0 < days_left < days_warning

    # warning in seconds (ensure seconds take precedence over days config)
    seconds_warning = days_warning * 24 * 3600
    instance = {'url': 'https://valid.mock/', 'days_warning': 0, 'seconds_warning': seconds_warning}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path, check_hostname)
    assert status == AgentCheck.WARNING
    assert 0 < seconds_left < seconds_warning


@pytest.mark.usefixtures("dd_environment")
def test_check_ssl(aggregator, http_check):
    # Run the check for all the instances in the config
    for instance in CONFIG_SSL_ONLY['instances']:
        http_check.check(instance)

    good_cert_tags = ['url:https://valid.mock:443', 'instance:good_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=good_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=good_cert_tags, count=1)

    expiring_soon_cert_tags = ['url:https://valid.mock', 'instance:cert_exp_soon']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expiring_soon_cert_tags, count=1)
    aggregator.assert_service_check(
        HTTPCheck.SC_SSL_CERT, status=HTTPCheck.WARNING, tags=expiring_soon_cert_tags, count=1
    )

    critical_cert_tags = ['url:https://valid.mock', 'instance:cert_critical']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=critical_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=critical_cert_tags, count=1)

    connection_err_tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_tsl_ca_cert(aggregator):
    instance = {
        'name': 'good_cert',
        'url': 'https://valid.mock:443',
        'timeout': 1,
        'tls_ca_cert': os.path.join(HERE, 'fixtures', 'cacert.pem'),
        'check_certificate_expiration': 'false',
        'collect_response_time': 'false',
        'disable_ssl_validation': 'false',
        'skip_proxy': 'false',
    }

    with mock.patch(
        'datadog_checks.http_check.http_check.get_ca_certs_path',
        new=lambda: os.path.join(HERE, 'fixtures', 'emptycert.pem'),
    ):
        check = HTTPCheck('http_check', {}, [instance])

    check.check(instance)
    good_cert_tags = ['url:https://valid.mock:443', 'instance:good_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=good_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_ssl_expire_error(aggregator, http_check):
    with mock.patch('ssl.SSLSocket.getpeercert', side_effect=Exception()):
        # Run the check for the one instance configured with days left
        http_check = HTTPCheck('', {}, [CONFIG_EXPIRED_SSL['instances'][0]])
        http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_ssl_expire_error_secs(aggregator, http_check):
    with mock.patch('ssl.SSLSocket.getpeercert', side_effect=Exception()):
        # Run the check for the one instance configured with seconds left
        http_check.check(CONFIG_EXPIRED_SSL['instances'][1])

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert_seconds']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_hostname_override(aggregator, http_check):

    # Run the check for all the instances in the config
    for instance in CONFIG_CUSTOM_NAME['instances']:
        http_check.check(instance)

    cert_validation_fail_tags = ['url:https://valid.mock:443', 'instance:cert_validation_fails']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_fail_tags, count=1)
    aggregator.assert_service_check(
        HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=cert_validation_fail_tags, count=1
    )

    cert_validation_pass_tags = ['url:https://valid.mock:443', 'instance:cert_validation_passes']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_pass_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=cert_validation_pass_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_allow_redirects(aggregator, http_check):

    # Run the check for the one instance
    http_check.check(CONFIG_HTTP_REDIRECTS['instances'][0])

    redirect_service_tags = ['url:https://valid.mock/301', 'instance:redirect_service']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=redirect_service_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_mock_case(aggregator, http_check):
    with mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT):
        # Run the check for the one instance
        http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_service_check_instance_name_normalization(aggregator, http_check):
    """
    Service check `instance` tag value is normalized.
    Note: necessary to avoid mismatch and backward incompatibility.
    """

    # Run the check for the one instance
    http_check.check(CONFIG_UNORMALIZED_INSTANCE_NAME['instances'][0])

    # Assess instance name normalization
    normalized_tags = ['url:https://valid.mock', 'instance:need_to_be_normalized']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=normalized_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=normalized_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_dont_check_expiration(aggregator, http_check):

    # Run the check for the one instance
    instance = CONFIG_DONT_CHECK_EXP['instances'][0]
    http_check.check(instance)

    url_tag = ['url:{}'.format(instance.get('url'))]
    instance_tag = ['instance:{}'.format(instance.get('name'))]

    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=url_tag + instance_tag, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, tags=url_tag + instance_tag, count=0)


@pytest.mark.usefixtures("dd_environment")
def test_data_methods(aggregator, http_check):

    # Run the check once for both POST configs
    for instance in CONFIG_DATA_METHOD['instances']:
        http_check.check(instance)

        url_tag = ['url:{}'.format(instance.get('url'))]
        instance_tag = ['instance:{}'.format(instance.get('name'))]

        aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.OK, tags=url_tag + instance_tag, count=1)
        aggregator.assert_metric('network.http.can_connect', tags=url_tag + instance_tag, value=1.0, count=1)
        aggregator.assert_metric('network.http.cant_connect', tags=url_tag + instance_tag, value=0.0, count=1)
        aggregator.assert_metric('network.http.response_time', tags=url_tag + instance_tag, count=1)

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
        aggregator.reset()


def test_unexisting_ca_cert_should_throw_error(aggregator):
    instance = {
        'name': 'Test Web VM HTTPS SSL',
        'url': 'https://foo.bar.net/',
        'method': 'get',
        'tls_ca_cert': '/tmp/unexisting.crt',
        'check_certificate_expiration': 'false',
        'collect_response_time': 'false',
        'disable_ssl_validation': 'false',
        'skip_proxy': 'false',
    }

    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    check.check(instance)
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.CRITICAL)
    assert 'invalid path: /tmp/unexisting.crt' in aggregator._service_checks[HTTPCheck.SC_STATUS][0].message
