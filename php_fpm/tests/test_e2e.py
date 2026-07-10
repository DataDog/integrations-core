# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.php_fpm import PHPFPMCheck

pytestmark = pytest.mark.e2e

METRICS = [
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


def test_status(dd_agent_check, instance, ping_url_tag):
    instance['tags'] = ['fpm_cluster:forums']

    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in METRICS:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=ServiceCheck.OK, tags=expected_tags)


def test_status_fastcgi(dd_agent_check, instance_fastcgi, ping_url_tag_fastcgi):
    instance_fastcgi['tags'] = ['fpm_cluster:forums']

    aggregator = dd_agent_check(instance_fastcgi, rate=True)

    expected_tags = ['fpm_cluster:forums', 'pool:www']
    for metric in METRICS:
        aggregator.assert_metric(metric, tags=expected_tags)

    expected_tags = [ping_url_tag_fastcgi, 'fpm_cluster:forums']
    aggregator.assert_service_check('php_fpm.can_ping', status=ServiceCheck.OK, tags=expected_tags)


def test_e2e_discovery(dd_agent_check_discovery):
    # The test fixture runs the official `php:7-fpm` image, whose short image name is
    # `php` -- too generic to use as an ad_identifier (it also matches php:cli, php:apache,
    # etc., which don't run FPM at all). The auto_conf.yaml therefore uses the more specific
    # `php-fpm` identifier (matching e.g. bitnami/php-fpm), which this fixture's image never
    # matches, so real Agent-side container discovery can't be exercised end-to-end here.
    # test_e2e_discovery_all_candidates below still validates that the generated candidate
    # config works against this container by calling generate_configs() directly.
    pytest.skip("test fixture image 'php:7-fpm' does not match the 'php-fpm' ad_identifier")

    aggregator = dd_agent_check_discovery(rate=True)

    expected_tags = ['pool:www']
    for metric in METRICS:
        aggregator.assert_metric(metric, tags=expected_tags)

    # discovery can't know the ping_url tag value ahead of time (it embeds the
    # container's dynamically-assigned IP), so only the service check name and
    # status are asserted here, not its tags.
    aggregator.assert_service_check('php_fpm.can_ping', status=ServiceCheck.OK)


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, PHPFPMCheck, compose_service='php')
