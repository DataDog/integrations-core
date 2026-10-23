# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.php_fpm.php_fpm import BadConfigError, PHPFPMCheck


class FooException(Exception):
    pass


def test_bad_config(check):
    with pytest.raises(BadConfigError):
        check.check({})


def test_bad_status(aggregator, dd_run_check):
    instance = {'status_url': 'http://foo:9001/status', 'tags': ['expectedbroken']}
    check = PHPFPMCheck('php_fpm', {}, [instance])
    dd_run_check(check)
    assert len(aggregator.metric_names) == 0


def test_bad_ping(aggregator, dd_run_check):
    instance = {'ping_url': 'http://foo:9001/ping', 'tags': ['some_tag']}
    check = PHPFPMCheck('php_fpm', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'php_fpm.can_ping', status=check.CRITICAL, tags=['ping_url:http://foo:9001/ping', 'some_tag']
    )
    aggregator.all_metrics_asserted()


def test_should_not_retry(fake_http, check, instance):
    """Non-503 errors must not be retried."""
    endpoint = instance['status_url']
    fake_http.register_response('GET', endpoint, FooException('Generic http error here'))
    with pytest.raises(FooException):
        check._process_status(endpoint, [], None, False)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]


def test_should_bail_out(fake_http, fake_http_response, check, instance):
    """Backoff gives up after three attempts."""
    endpoint = instance['status_url']
    for _ in range(3):
        fake_http_response(endpoint, status_code=503)
    with pytest.raises(HTTPClientStatusError):
        check._process_status(endpoint, [], None, False)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)] * 3


def test_backoff_success(fake_http, fake_http_response, check, instance, aggregator, payload):
    """Success after two failed attempts."""
    instance['ping_url'] = None
    endpoint = instance['status_url']
    fake_http_response(endpoint, status_code=503)
    fake_http_response(endpoint, status_code=503)
    fake_http_response(endpoint, json_data=payload)
    pool_name = check._process_status(endpoint, [], None, False)
    assert pool_name == 'www'
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)] * 3


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("old auth config", {'user': 'old_foo', 'password': 'new_bar'}, {'auth': ('old_foo', 'new_bar')}),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'disable_ssl_validation': False}, {'verify': True}),
        ("legacy ssl config False", {'disable_ssl_validation': True}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': True}),
        (
            "http_host header",
            {"http_host": "foo"},
            {
                'headers': {
                    'User-Agent': 'Datadog Agent/0.0.0',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'foo',
                }
            },
        ),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs, dd_run_check, mocker):
    instance = {'ping_url': 'http://foo:9001/ping'}
    instance.update(extra_config)
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])

    get = mocker.patch.object(type(check.http), 'get', return_value=FakeHTTPResponse(text='pong'))
    dd_run_check(check)
    get.assert_called_once_with('http://foo:9001/ping')
    for option, expected in expected_http_kwargs.items():
        assert check.http.options[option] == expected
