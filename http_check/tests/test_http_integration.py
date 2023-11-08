# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import sys
from collections import OrderedDict

import mock
import pytest
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.http_check import HTTPCheck

from .common import (
    CONFIG_CUSTOM_NAME,
    CONFIG_DATA_METHOD,
    CONFIG_DONT_CHECK_EXP,
    CONFIG_EXPIRED_SSL,
    CONFIG_HTTP_ALLOW_REDIRECTS,
    CONFIG_HTTP_NO_REDIRECTS,
    CONFIG_SSL_ONLY,
    CONFIG_UNORMALIZED_INSTANCE_NAME,
    FAKE_CERT,
    HERE,
)
from .conftest import mock_get_ca_certs_path


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_up(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://valid.mock/'}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.OK
    assert days_left > 0
    assert seconds_left > 0


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_up_tls_verify_false(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://valid.mock/', 'tls_verify': False}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.UNKNOWN
    assert "Empty or no certificate found" in msg


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_up_tls_verify_false_tls_retrieve_non_validated_cert_true(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://valid.mock/', 'tls_verify': False, "tls_retrieve_non_validated_cert": True}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.OK
    assert days_left > 0
    assert seconds_left > 0


@pytest.mark.usefixtures("dd_environment")
def test_cert_expiration_no_cert(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://valid.mock/'}
    http_check.instance = instance

    with mock.patch('ssl.SSLSocket.getpeercert', return_value=None):

        status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
        assert status == AgentCheck.UNKNOWN
        expected_msg = 'Empty or no certificate found.'
        if PY2:
            expected_msg = (
                'ValueError(\'empty or no certificate, match_hostname needs a SSL socket '
                'or SSL context with either CERT_OPTIONAL or CERT_REQUIRED\',)'
            )
        assert msg == expected_msg


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_bad_hostname(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://wronghost.mock/'}
    http_check.instance = instance
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.UNKNOWN
    assert days_left is None
    assert seconds_left is None
    assert 'Hostname mismatch' in msg or "doesn't match" in msg


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_site_down(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://this.does.not.exist.foo'}
    http_check.instance = instance
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.UNKNOWN
    assert days_left is None
    assert seconds_left is None


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_cert_expired(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://expired.mock/'}
    http_check.instance = instance
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    if sys.version_info[0] < 3:
        # Python 2 returns ambiguous "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
        # Same as site is down
        assert status == AgentCheck.UNKNOWN
        assert days_left is None
        assert seconds_left is None
    else:
        assert status == AgentCheck.CRITICAL
        assert days_left == 0
        assert seconds_left == 0


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_critical(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')

    # in days
    days_critical = 200
    instance = {'url': 'https://valid.mock/', 'days_critical': days_critical}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.CRITICAL
    assert 0 < days_left < days_critical

    # in seconds (ensure seconds take precedence over days config)
    seconds_critical = days_critical * 24 * 3600
    instance = {'url': 'https://valid.mock/', 'days_critical': 0, 'seconds_critical': seconds_critical}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.CRITICAL
    assert 0 < seconds_left < seconds_critical


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_warning(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    # warning in days
    days_warning = 200
    instance = {'url': 'https://valid.mock/', 'days_warning': days_warning}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.WARNING
    assert 0 < days_left < days_warning

    # warning in seconds (ensure seconds take precedence over days config)
    seconds_warning = days_warning * 24 * 3600
    instance = {'url': 'https://valid.mock/', 'days_warning': 0, 'seconds_warning': seconds_warning}
    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)
    assert status == AgentCheck.WARNING
    assert 0 < seconds_left < seconds_warning


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_self_signed(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://selfsigned.mock/'}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.UNKNOWN
    if PY2:
        assert "certificate verify failed" in msg
    else:
        assert re.search("certificate verify failed: self[- ]signed certificate", msg)


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_self_signed_tls_verify_false_tls_retrieve_non_validated_cert_true(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://selfsigned.mock/', 'tls_verify': False, "tls_retrieve_non_validated_cert": True}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.OK
    assert days_left > 0
    assert seconds_left > 0


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_self_signed_tls_verify_false_tls_retrieve_non_validated_cert_false(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://selfsigned.mock/', 'tls_verify': False, "tls_retrieve_non_validated_cert": False}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.UNKNOWN
    assert "Empty or no certificate found" in msg


@pytest.mark.usefixtures("dd_environment")
def test_check_cert_expiration_self_signed_tls_verify_false_tls_retrieve_non_validated_cert_default(http_check):
    cert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    instance = {'url': 'https://selfsigned.mock/', 'tls_verify': False}
    http_check.instance = instance

    status, days_left, seconds_left, msg = http_check.check_cert_expiration(instance, 10, cert_path)

    assert status == AgentCheck.UNKNOWN
    assert "Empty or no certificate found" in msg


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
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=connection_err_tags, count=1)


@pytest.mark.usefixtures('dd_environment')
def test_check_ssl_use_cert_from_response(aggregator, http_check):
    # Run the check for all the instances in the config
    for instance in CONFIG_SSL_ONLY['instances']:
        instance = instance.copy()
        instance['use_cert_from_response'] = True
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
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=connection_err_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_tsl_ca_cert(aggregator, dd_run_check):
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

    dd_run_check(check)
    good_cert_tags = ['url:https://valid.mock:443', 'instance:good_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=good_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_ssl_expire_error(aggregator, dd_run_check):
    with mock.patch('ssl.SSLSocket.getpeercert', side_effect=Exception()):
        with mock.patch(
            'datadog_checks.http_check.http_check.get_ca_certs_path',
            new=lambda: os.path.join(HERE, 'fixtures', 'cacert.pem'),
        ):
            # Run the check for the one instance configured with days left
            http_check = HTTPCheck('', {}, [CONFIG_EXPIRED_SSL['instances'][0]])
            dd_run_check(http_check)

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=expired_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_ssl_expire_error_secs(aggregator, http_check):
    with mock.patch('ssl.SSLSocket.getpeercert', side_effect=Exception()):
        # Run the check for the one instance configured with seconds left
        http_check.check(CONFIG_EXPIRED_SSL['instances'][1])

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert_seconds']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=expired_cert_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_hostname_override(aggregator, http_check):

    # Run the check for all the instances in the config
    for instance in CONFIG_CUSTOM_NAME['instances']:
        http_check.check(instance)

    cert_validation_fail_tags = ['url:https://valid.mock:443', 'instance:cert_validation_fails']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_fail_tags, count=1)
    aggregator.assert_service_check(
        HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=cert_validation_fail_tags, count=1
    )

    cert_validation_pass_tags = ['url:https://valid.mock:443', 'instance:cert_validation_passes']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=cert_validation_pass_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=cert_validation_pass_tags, count=1)


@pytest.mark.usefixtures("dd_environment")
def test_check_allow_redirects(aggregator):
    with mock.patch('datadog_checks.http_check.http_check.get_ca_certs_path', new=mock_get_ca_certs_path):
        http_check = HTTPCheck('http_check', {}, CONFIG_HTTP_NO_REDIRECTS["instances"])
        # Run the check for the one instance
        http_check.check(CONFIG_HTTP_NO_REDIRECTS['instances'][0])
        redirect_service_tags = ['url:https://valid.mock/301', 'instance:no_allow_redirect_service']
        aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=redirect_service_tags, count=1)

        redirect_service_tags = ['url:https://valid.mock/301', 'instance:allow_redirect_service']
        http_check.check(CONFIG_HTTP_ALLOW_REDIRECTS['instances'][0])
        aggregator.assert_service_check(
            HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=redirect_service_tags, count=1
        )


@pytest.mark.usefixtures("dd_environment")
def test_mock_case(aggregator, http_check):
    with mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT):
        # Run the check for the one instance
        http_check.check(CONFIG_EXPIRED_SSL['instances'][0])

    expired_cert_tags = ['url:https://valid.mock', 'instance:expired_cert']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    if sys.version_info[0] < 3:
        aggregator.assert_service_check(
            HTTPCheck.SC_SSL_CERT, status=HTTPCheck.UNKNOWN, tags=expired_cert_tags, count=1
        )
    else:
        aggregator.assert_service_check(
            HTTPCheck.SC_SSL_CERT, status=HTTPCheck.CRITICAL, tags=expired_cert_tags, count=1
        )


@pytest.mark.usefixtures("dd_environment")
@pytest.mark.parametrize(
    ["config", "cert", "password"],
    [
        ({'tls_cert': 'foo'}, 'foo', None),
        ({'tls_cert': 'foo', 'tls_private_key': 'bar'}, 'foo', 'bar'),
        ({'client_cert': 'foo'}, 'foo', None),
        ({'client_cert': 'foo', 'client_key': 'bar'}, 'foo', 'bar'),
    ],
)
def test_client_certs_are_passed(aggregator, http_check, config, cert, password):
    instance = {'url': 'https://valid.mock', 'name': 'baz'}
    instance.update(config)
    # Run the check for the one instance
    http_check.check(instance)

    expired_cert_tags = ['url:https://valid.mock', 'instance:baz']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=HTTPCheck.OK, tags=expired_cert_tags, count=1)


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


def test_unexisting_ca_cert_should_throw_error(aggregator, dd_run_check):
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

    dd_run_check(check)
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.CRITICAL)
    assert 'invalid path: /tmp/unexisting.crt' in aggregator._service_checks[HTTPCheck.SC_STATUS][0].message


def test_instance_auth_token(dd_run_check):
    token_path = os.path.join(HERE, 'fixtures', 'token.txt')
    with open(token_path, 'r') as t:
        data = t.read()
    auth_token = {
        "reader": {
            "type": "file",
            "path": token_path,
        },
        "writer": {"type": "header", "name": "Authorization"},
    }

    expected_headers = OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip, deflate'),
            ('Authorization', str(data)),
        ]
    )

    instance = {'url': 'https://valid.mock', 'name': 'UpService', "auth_token": auth_token}
    check = HTTPCheck('http_check', {'ca_certs': mock_get_ca_certs_path()}, [instance])
    dd_run_check(check)
    assert expected_headers == check.http.options['headers']
    dd_run_check(check)
    assert expected_headers == check.http.options['headers']


@pytest.mark.parametrize(
    ["instance", "expected_headers"],
    [
        (
            {'url': 'https://valid.mock', 'name': 'UpService', 'extra_headers': {'Host': 'test'}},
            OrderedDict(
                [
                    ('User-Agent', 'Datadog Agent/0.0.0'),
                    ('Accept', '*/*'),
                    ('Accept-Encoding', 'gzip, deflate'),
                    ('Host', 'test'),
                ]
            ),
        ),
        (
            {'url': 'https://valid.mock', 'name': 'UpService', 'headers': {'Host': 'test'}},
            OrderedDict(
                [
                    ('Host', 'test'),
                ]
            ),
        ),
        ({'url': 'https://valid.mock', 'name': 'UpService', 'include_default_headers': False}, OrderedDict()),
    ],
)
def test_expected_headers(dd_run_check, instance, expected_headers):

    check = HTTPCheck('http_check', {'ca_certs': mock_get_ca_certs_path()}, [instance])
    dd_run_check(check)
    assert expected_headers == check.http.options['headers']

    dd_run_check(check)
    assert expected_headers == check.http.options['headers']


@pytest.mark.parametrize(
    'instance, check_hostname',
    [
        pytest.param(
            {
                'url': 'https://valid.mock',
                'name': 'UpService',
                'tls_verify': True,
                'check_hostname': False,
            },
            False,
            id='check_hostname disabled',
        ),
        pytest.param(
            {
                'url': 'https://valid.mock',
                'name': 'UpService',
                'tls_verify': True,
                'check_hostname': True,
            },
            True,
            id='check_hostname enabled',
        ),
        pytest.param(
            {
                'url': 'https://valid.mock',
                'name': 'UpService',
                'tls_verify': False,
                'check_hostname': True,
            },
            False,
            id='tls not verify',
        ),
    ],
)
def test_tls_config_ok(dd_run_check, instance, check_hostname):
    check = HTTPCheck(
        'http_check',
        {'ca_certs': mock_get_ca_certs_path()},
        [instance],
    )
    tls_context = check.get_tls_context()
    assert tls_context.check_hostname is check_hostname


@pytest.mark.parametrize(
    'headers',
    [
        pytest.param({'content-type': 'application/json'}),
        pytest.param({'Content-Type': 'application/json'}),
        pytest.param({'CONTENT-TYPE': 'text/html'}),
        pytest.param({}),
    ],
)
def test_case_insensitive_header_content_type(dd_run_check, headers):
    """
    Test that `Content-Type` is accessible from the headers dict regardless of letter case.
    We're only testing `Content-Type` for a non-GET method because that's the only header field
    that applies a default header value if omitted.
    """
    instance = {
        'name': 'foobar',
        'url': 'http://something.com',
        'method': 'POST',
        'headers': headers,
        'data': {'foo': 'bar'},
    }
    default_headers = {
        'User-Agent': 'Datadog Agent/0.0.0',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    dd_run_check(check)

    if headers == {}:
        assert check.http.options["headers"] == default_headers
    else:
        assert check.http.options["headers"] == headers


def test_http_response_status_code_accepts_int_value(aggregator, dd_run_check):
    instance = {
        'name': 'foobar',
        'url': 'http://something.com',
        'http_response_status_code': 404,
    }
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    dd_run_check(check)
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.CRITICAL)
