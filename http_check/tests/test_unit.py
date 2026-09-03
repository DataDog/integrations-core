# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import socket
from datetime import timedelta

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientInvalidURLError,
    HTTPClientRequestError,
    HTTPClientSSLError,
    HTTPClientStatusError,
    HTTPClientTimeoutError,
)
from datadog_checks.http_check import HTTPCheck, http_check


def test__init__():
    # empty values should be ignored
    init_config = {'ca_certs': ''}
    # `get_ca_certs_path` needs to be mocked because it's used as fallback when
    # init_config doesn't contain `ca_certs`
    with mock.patch('datadog_checks.http_check.http_check.get_ca_certs_path', return_value='bar'):
        http_check = HTTPCheck('http_check', init_config, [{}])
        assert http_check.ca_certs == 'bar'

    # normal case
    init_config = {'ca_certs': 'foo'}
    http_check = HTTPCheck('http_check', init_config, [{}])
    assert http_check.ca_certs == 'foo'


def test_instances_do_not_share_data():
    http_check_1 = HTTPCheck('http_check', {'ca_certs': 'foo'}, [{}])
    http_check_1.HTTP_CONFIG_REMAPPER['ca_certs']['default'] = 'foo'
    http_check_2 = HTTPCheck('http_check', {'ca_certs': 'bar'}, [{}])
    http_check_2.HTTP_CONFIG_REMAPPER['ca_certs']['default'] = 'bar'

    assert http_check_1.HTTP_CONFIG_REMAPPER['ca_certs']['default'] == 'foo'
    assert http_check_2.HTTP_CONFIG_REMAPPER['ca_certs']['default'] == 'bar'


def test_message_lenght_when_content_is_too_long():
    max_lenght = http_check.MESSAGE_LENGTH
    try:
        http_check.MESSAGE_LENGTH = 25
        too_long_content = 'this message is too long'
        error_message = 'There has been an error.'
        message = HTTPCheck._include_content(True, error_message, too_long_content)
    finally:
        http_check.MESSAGE_LENGTH = max_lenght

    assert len(message) == 25
    assert error_message in message
    assert too_long_content not in message


def test_message_lenght_when_content_is_ok():
    content = '''{
    "HikariPool-1.pool.ConnectivityCheck" : {
        "healthy" : true
    },
    "database" : {
        "healthy" : true,
        "message" : "Service located at jdbc ostgresql://pgbouncer-server.staging.net is alive. Version: 1.5"
    },
    "deadlocks" : {
        "healthy" : true
    }
    "gateway" : {
        "healthy" : true,
        "message" : "Service located at https://apis.staging.eu.people-doc.com is alive."
    }
}'''
    error_message = 'There has been an error.'
    message = HTTPCheck._include_content(True, error_message, content)

    assert len(message) < http_check.MESSAGE_LENGTH
    assert content in message
    assert error_message in message


def test_message_when_content_is_disabled():
    content = "This is not part of the message"
    error_message = 'There has been an error.'
    message = HTTPCheck._include_content(False, error_message, content)

    assert message == error_message
    assert content not in message


def test_invalid_url_submits_critical_service_check(aggregator, fake_http) -> None:
    instance = {'name': 'invalid_url', 'url': 'https://example.com', 'check_certificate_expiration': False}
    fake_http.register_response('GET', instance['url'], HTTPClientInvalidURLError('Invalid URL'))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    check.check(instance)

    tags = ['url:https://example.com', 'instance:invalid_url']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=tags, count=1)


def test_generic_request_error_submits_critical_service_check(aggregator, fake_http) -> None:
    instance = {'name': 'request_error', 'url': 'https://example.com', 'check_certificate_expiration': False}
    fake_http.register_response('GET', instance['url'], HTTPClientRequestError('Request failed'))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    check.check(instance)

    tags = ['url:https://example.com', 'instance:request_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=tags, count=1)


def test_check_closes_http_client(aggregator, fake_http):
    instance = {'name': 'lifecycle', 'url': 'https://example.com', 'check_certificate_expiration': False}
    fake_http.register_response('GET', instance['url'], _mock_response(200))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    check.check(instance)

    assert check.http.closed is True


def test_post_sets_content_type_header(fake_http):
    instance = {
        'name': 'content_type',
        'url': 'https://example.com/submit',
        'method': 'post',
        'check_certificate_expiration': False,
    }
    fake_http.register_response('POST', instance['url'], _mock_response(200))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    check.check(instance)

    assert check.http.get_header('Content-Type') == 'application/x-www-form-urlencoded'


URL = 'http://foo.bar'
URL_TAG = 'url:{}'.format(URL)
INSTANCE_TAG = 'instance:http_outcome_tag'


def _mock_response(status_code):
    return FakeHTTPResponse(content=b'hello', text='hello', status_code=status_code, elapsed=timedelta(seconds=0.5))


def _make_check(**extra):
    instance = {'name': 'http_outcome_tag', 'url': URL, 'timeout': 1}
    instance.update(extra)
    return HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance]), instance


def test_missing_response_cert_does_not_open_second_connection(aggregator, fake_http, caplog):
    instance = {
        'name': 'missing_response_cert',
        'url': 'https://example.com',
        'timeout': 1,
        'use_cert_from_response': True,
    }
    message = 'Unable to retrieve the peer certificate from the HTTP response.'
    caplog.set_level('DEBUG')
    fake_http.register_response('GET', instance['url'], FakeHTTPResponse(peer_cert=None))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    with mock.patch.object(
        check, '_fetch_cert', side_effect=AssertionError('opened a second TLS connection')
    ) as fetch_cert:
        check.check(instance)

    fetch_cert.assert_not_called()
    aggregator.assert_service_check(HTTPCheck.SC_SSL_CERT, status=AgentCheck.UNKNOWN, message=message, count=1)
    assert message in caplog.text


def test_request_failure_still_reports_expired_certificate(aggregator, fake_http):
    instance = {
        'name': 'request_failure',
        'url': 'https://example.com',
        'timeout': 1,
        'use_cert_from_response': True,
    }
    message = 'certificate has expired'
    fake_http.register_response('GET', instance['url'], HTTPClientSSLError(message))
    check = HTTPCheck('http_check', {'ca_certs': 'foo'}, [instance])

    with mock.patch.object(
        check,
        'check_cert_expiration',
        return_value=(AgentCheck.CRITICAL, 0, 0, message),
    ):
        check.check(instance)

    tags = ['url:https://example.com', 'instance:request_failure']
    aggregator.assert_metric('http.ssl.days_left', value=0, tags=tags, count=1)
    aggregator.assert_metric('http.ssl.seconds_left', value=0, tags=tags, count=1)
    aggregator.assert_service_check(
        HTTPCheck.SC_SSL_CERT,
        status=AgentCheck.CRITICAL,
        tags=tags,
        message=message,
        count=1,
    )


def test_http_outcome_tag_absent_by_default(aggregator, fake_http):
    """Without `enable_http_outcome_tag`, no metric carries an `http_outcome` tag."""
    check, instance = _make_check()
    fake_http.register_response('GET', URL, _mock_response(200))

    check.check(instance)

    expected_tags = [URL_TAG, INSTANCE_TAG]
    aggregator.assert_metric('network.http.can_connect', value=1.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.cant_connect', value=0.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.response_time', value=0.5, tags=expected_tags, count=1)


@pytest.mark.parametrize(
    'status_code, can_connect, cant_connect',
    [
        pytest.param(200, 1.0, 0.0, id='2xx response'),
        pytest.param(500, 0.0, 1.0, id='non-2xx response'),
    ],
)
def test_http_outcome_tag_added_when_enabled(aggregator, fake_http, status_code, can_connect, cant_connect):
    """All three metrics carry the numeric status code, including for error responses."""
    check, instance = _make_check(enable_http_outcome_tag=True)
    fake_http.register_response('GET', URL, _mock_response(status_code))

    check.check(instance)

    expected_tags = [URL_TAG, INSTANCE_TAG, 'http_outcome:{}'.format(status_code)]
    aggregator.assert_metric('network.http.can_connect', value=can_connect, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.cant_connect', value=cant_connect, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.response_time', value=0.5, tags=expected_tags, count=1)


def test_http_outcome_tag_reports_status_code_when_content_match_fails(aggregator, fake_http):
    """`http_outcome` is what HTTP returned, not the verdict: a 200 that fails `content_match` is down."""
    check, instance = _make_check(enable_http_outcome_tag=True, content_match='not in the body')
    fake_http.register_response('GET', URL, _mock_response(200))

    check.check(instance)

    expected_tags = [URL_TAG, INSTANCE_TAG, 'http_outcome:200']
    aggregator.assert_metric('network.http.can_connect', value=0.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.cant_connect', value=1.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.response_time', value=0.5, tags=expected_tags, count=1)
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.CRITICAL, count=1)


@pytest.mark.parametrize(
    'error, expected_value',
    [
        pytest.param(HTTPClientSSLError('bad cert'), 'ssl_error', id='ssl_error'),
        pytest.param(HTTPClientConnectTimeoutError('too slow'), 'timeout', id='connect_timeout'),
        pytest.param(HTTPClientTimeoutError('too slow'), 'timeout', id='timeout'),
        pytest.param(socket.timeout('too slow'), 'timeout', id='socket_timeout'),
        pytest.param(HTTPClientConnectionError('refused'), 'connection_error', id='connection_error'),
        pytest.param(OSError('no such file'), 'socket_error', id='socket_error'),
        pytest.param(HTTPClientStatusError('503 Server Error'), 'socket_error', id='status_error'),
    ],
)
def test_http_outcome_tag_on_failure_paths(aggregator, fake_http, error, expected_value):
    """When no response is received the tag falls back to a sentinel and no response time is reported."""
    check, instance = _make_check(enable_http_outcome_tag=True)
    fake_http.register_response('GET', URL, error)

    check.check(instance)

    expected_tags = [URL_TAG, INSTANCE_TAG, 'http_outcome:{}'.format(expected_value)]
    aggregator.assert_metric('network.http.can_connect', value=0.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.cant_connect', value=1.0, tags=expected_tags, count=1)
    aggregator.assert_metric('network.http.response_time', count=0)
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=AgentCheck.CRITICAL, count=1)
