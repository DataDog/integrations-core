# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("dd_environment")
]


def test_bad_ping_reply(check, instance, aggregator, ping_url_tag):
    instance['status_url'] = None
    instance['ping_reply'] = 'foo'
    instance['tags'] = ['expectedbroken']
    expected_tags = [ping_url_tag, 'expectedbroken']

    check.check(instance)

    aggregator.assert_service_check('php_fpm.can_ping', status=check.CRITICAL, tags=expected_tags)
    aggregator.all_metrics_asserted()


def test_status(check, instance, aggregator, ping_url_tag):
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


def test_status_fastcgi(check, instance_fastcgi, aggregator, ping_url_tag_fastcgi):
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
