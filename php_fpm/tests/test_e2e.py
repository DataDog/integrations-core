# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.php_fpm import PHPFPMCheck

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


def test_e2e_discovery(dd_agent_check_discovery):
    # The test image 'php:7-fpm' has short name 'php', which does not match
    # the ad_identifier 'php-fpm'. Discovery works with images like 'bitnami/php-fpm'.
    pytest.skip("Test environment uses 'php:7-fpm' (short name 'php'); discovery requires an image with 'php-fpm' in its name")
    aggregator = dd_agent_check_discovery(check_rate=True)

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, check_symmetric_inclusion=False
    )
    aggregator.assert_service_check('php_fpm.can_connect', status=PHPFPMCheck.OK)
