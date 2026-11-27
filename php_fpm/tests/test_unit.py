# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

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
    assert len(fake_http.requests) == 1


def test_should_bail_out(check, instance, fake_http, fake_http_response):
    """
    backoff should give up after 3 attempts
    """
    for _ in range(3):
        fake_http_response(instance['status_url'], status_code=503, once=True)
    fake_http_response(instance['status_url'], status_code=200, once=True)

    with pytest.raises(HTTPClientStatusError):
        check._process_status(instance['status_url'], [], None, False)
    assert len(fake_http.requests) == 3


def test_backoff_success(check, instance, aggregator, payload, fake_http_response):
    """
    Success after 2 failed attempts
    """
    instance['ping_url'] = None
    fake_http_response(instance['status_url'], status_code=503, once=True)
    fake_http_response(instance['status_url'], status_code=503, once=True)
    fake_http_response(instance['status_url'], json_data=payload, once=True)

    pool_name = check._process_status(instance['status_url'], [], None, False)
    assert pool_name == 'www'


@pytest.mark.parametrize(
    'test_case, extra_config, expected_options',
    [
        ("old auth config", {'user': 'old_foo', 'password': 'new_bar'}, {'auth': ('old_foo', 'new_bar')}),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'disable_ssl_validation': False}, {'verify': True}),
        ("legacy ssl config False", {'disable_ssl_validation': True}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': True}),
    ],
)
def test_config(test_case, extra_config, expected_options):
    # Configuration resolves when the client is created, so the check is built without fake_http and never run.
    instance = {'ping_url': 'http://foo:9001/ping'}
    instance.update(extra_config)
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])

    for option, value in expected_options.items():
        assert check.http.options[option] == value


@pytest.mark.parametrize('headers', [{}, {'host': 'bar'}], ids=['no user header', 'user host header'])
def test_http_host_sets_host_header(headers):
    instance = {'ping_url': 'http://foo:9001/ping', 'http_host': 'foo', 'headers': headers}
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])

    assert check.http.get_header('Host') == 'foo'
