# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.php_fpm.php_fpm import PHPFPMCheck

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_bad_ping_reply(instance, aggregator, ping_url_tag, dd_run_check):
    instance['status_url'] = None
    instance['ping_reply'] = 'foo'
    instance['tags'] = ['expectedbroken']
    expected_tags = [ping_url_tag, 'expectedbroken']
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])

    dd_run_check(check)

    aggregator.assert_service_check('php_fpm.can_ping', status=check.CRITICAL, tags=expected_tags)
    aggregator.all_metrics_asserted()


def test_status(instance, aggregator, ping_url_tag, dd_run_check):
    instance['tags'] = ['fpm_cluster:forums']
    check = PHPFPMCheck('php_fpm', {}, instances=[instance])
    dd_run_check(check)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
        'php_fpm.status.duration',
    ]

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=check.OK, tags=expected_tags)


def test_status_fastcgi(instance_fastcgi, aggregator, ping_url_tag_fastcgi, dd_run_check):
    instance_fastcgi['tags'] = ['fpm_cluster:forums']
    check = PHPFPMCheck('php_fpm', {}, instances=[instance_fastcgi])
    dd_run_check(check)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
        'php_fpm.status.duration',
    ]

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag_fastcgi, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=check.OK, tags=expected_tags)
