# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest

from datadog_checks.php_fpm.php_fpm import BadConfigError, PHPFPMCheck


class FooException(Exception):
    pass


def test_bad_config(check):
    with pytest.raises(BadConfigError):
        check.check({})


def test_bad_status(aggregator):
    instance = {'status_url': 'http://foo:9001/status', 'tags': ['expectedbroken']}
    check = PHPFPMCheck('php_fpm', {}, [instance])
    check.check(instance)
    assert len(aggregator.metric_names) == 0


def test_bad_ping(aggregator):
    instance = {'ping_url': 'http://foo:9001/ping', 'tags': ['some_tag']}
    check = PHPFPMCheck('php_fpm', {}, [instance])
    check.check(instance)
    aggregator.assert_service_check(
        'php_fpm.can_ping', status=check.CRITICAL, tags=['ping_url:http://foo:9001/ping', 'some_tag']
    )
    aggregator.all_metrics_asserted()


def test_should_not_retry(check, instance):
    """
    backoff only works when response code is 503, otherwise the error
    should bubble up
    """
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = FooException("Generic http error here")
        with pytest.raises(FooException):
            check._process_status(instance['status_url'], [], None, False)


def test_should_bail_out(check, instance):
    """
    backoff should give up after 3 attempts
    """
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        attrs = {'raise_for_status.side_effect': FooException()}
        r.get.side_effect = [
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=200),
        ]
        with pytest.raises(FooException):
            check._process_status(instance['status_url'], [], None, False)


def test_backoff_success(check, instance, aggregator, payload):
    """
    Success after 2 failed attempts
    """
    instance['ping_url'] = None
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        attrs = {}
        r.get.side_effect = [
            mock.MagicMock(status_code=503),
            mock.MagicMock(status_code=503),
            mock.MagicMock(status_code=200, **attrs),
        ]
        pool_name = check._process_status(instance['status_url'], [], None, False)
        assert pool_name == 'www'
