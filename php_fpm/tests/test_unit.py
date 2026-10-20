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


def test_should_not_retry(check, instance, fake_http):
    """
    backoff only works when response code is 503, otherwise the error
    should bubble up
    """
    fake_http.register_response('GET', instance['status_url'], FooException("Generic http error here"))
    with pytest.raises(FooException):
        check._process_status(instance['status_url'], [], None, False)


def test_should_bail_out(check, instance, fake_http):
    """
    backoff should give up after 3 attempts
    """
    for _ in range(3):
        fake_http.register_response('GET', instance['status_url'], FakeHTTPResponse(status_code=503))
    fake_http.register_response('GET', instance['status_url'], FakeHTTPResponse(status_code=200, json_result={}))
    with pytest.raises(HTTPClientStatusError):
        check._process_status(instance['status_url'], [], None, False)

    assert len(fake_http.requests) == 3


def test_backoff_success(check, instance, aggregator, payload, fake_http, fake_http_response):
    """
    Success after 2 failed attempts
    """
    instance['ping_url'] = None
    for _ in range(2):
        fake_http.register_response('GET', instance['status_url'], FakeHTTPResponse(status_code=503))
    fake_http_response(instance['status_url'], json_data=payload)
    pool_name = check._process_status(instance['status_url'], [], None, False)
    assert pool_name == 'www'


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
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = {'ping_url': 'http://foo:9001/ping'}
    instance.update(extra_config)
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])

    for key, value in expected_http_kwargs.items():
        # The header mapping is compared whole, so a header the case should not carry at all, an
        # Authorization alongside http_host for instance, fails here.
        assert check.http.options[key] == value
