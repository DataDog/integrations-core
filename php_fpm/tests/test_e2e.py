# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

pytestmark = pytest.mark.e2e


def test_status(dd_agent_check, instance, ping_url_tag):
    instance['tags'] = ['fpm_cluster:forums']

    aggregator = dd_agent_check(instance, rate=True)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
        'php_fpm.processes.max_active',
        'php_fpm.status.duration',
    ]

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=ServiceCheck.OK, tags=expected_tags)


def test_status_fastcgi(dd_agent_check, instance_fastcgi, ping_url_tag_fastcgi):
    instance_fastcgi['tags'] = ['fpm_cluster:forums']

    aggregator = dd_agent_check(instance_fastcgi, rate=True)

    metrics = [
        'php_fpm.listen_queue.size',
        'php_fpm.processes.idle',
        'php_fpm.processes.active',
        'php_fpm.processes.total',
        'php_fpm.requests.slow',
        'php_fpm.requests.accepted',
        'php_fpm.processes.max_reached',
        'php_fpm.processes.max_active',
        'php_fpm.status.duration',
    ]

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in metrics:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag_fastcgi, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=ServiceCheck.OK, tags=expected_tags)
