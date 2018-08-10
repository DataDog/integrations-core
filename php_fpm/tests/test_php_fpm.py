# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
import mock

from datadog_checks.php_fpm.php_fpm import BadConfigError


class FooException(Exception):
    pass


def test_bad_config(check):
    with pytest.raises(BadConfigError):
        check.check({})


def test_bad_status(check, aggregator):
    instance = {
        'status_url': 'http://foo:9001/status',
        'tags': ['expectedbroken']
    }
    check.check(instance)
    assert len(aggregator.metric_names) == 0


def test_bad_ping(check, instance, aggregator, ping_url_tag):
    check.check(instance)
    aggregator.assert_service_check('php_fpm.can_ping', status=check.CRITICAL, tags=[ping_url_tag])
    aggregator.all_metrics_asserted()


@pytest.mark.integration
def test_bad_ping_reply(check, instance, aggregator, ping_url_tag, php_fpm_instance):
    instance['status_url'] = None
    instance['ping_reply'] = 'foo'
    instance['tags'] = ['expectedbroken']
    expected_tags = [ping_url_tag, 'expectedbroken']

    check.check(instance)

    aggregator.assert_service_check('php_fpm.can_ping', status=check.CRITICAL, tags=expected_tags)
    aggregator.all_metrics_asserted()


@pytest.mark.integration
def test_status(check, instance, aggregator, ping_url_tag, php_fpm_instance):
    instance['tags'] = ['cluster:forums']
    check.check(instance)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
    ]

    expected_tags = ['cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag, 'cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=check.OK, tags=expected_tags)


@pytest.mark.integration
def test_status_fastcgi(check, instance_fastcgi, aggregator, ping_url_tag_fastcgi, php_fpm_instance):
    instance_fastcgi['tags'] = ['cluster:forums']
    check.check(instance_fastcgi)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
    ]

    expected_tags = ['cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag_fastcgi, 'cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=check.OK, tags=expected_tags)


def test_should_not_retry(check, instance):
    """
    backoff only works when response code is 503, otherwise the error
    should bubble up
    """
    with mock.patch('datadog_checks.php_fpm.php_fpm.requests') as r:
        r.get.side_effect = FooException("Generic http error here")
        with pytest.raises(FooException):
            check._process_status(instance['status_url'], None, [], None, 10, True, False)


def test_should_bail_out(check, instance):
    """
    backoff should give up after 3 attempts
    """
    with mock.patch('datadog_checks.php_fpm.php_fpm.requests') as r:
        attrs = {'raise_for_status.side_effect': FooException()}
        r.get.side_effect = [
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=503, **attrs),
            mock.MagicMock(status_code=200),
        ]
        with pytest.raises(FooException):
            check._process_status(instance['status_url'], None, [], None, 10, True, False)


def test_backoff_success(check, instance, aggregator, payload):
    """
    Success after 2 failed attempts
    """
    instance['ping_url'] = None
    with mock.patch('datadog_checks.php_fpm.php_fpm.requests') as r:
        attrs = {'json.return_value': payload}
        r.get.side_effect = [
            mock.MagicMock(status_code=503),
            mock.MagicMock(status_code=503),
            mock.MagicMock(status_code=200, **attrs),
        ]
        pool_name = check._process_status(instance['status_url'], None, [], None, 10, True, False)
        assert pool_name == 'www'
