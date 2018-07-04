# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.php_fpm import BadConfigError

# sample from /status?json
# {
#    "pool":"www",
#    "process manager":"dynamic",
#    "start time":1530722898,
#    "start since":12,
#    "accepted conn":2,
#    "listen queue":0,
#    "max listen queue":0,
#    "listen queue len":128,
#    "idle processes":1,
#    "active processes":1,
#    "total processes":2,
#    "max active processes":1,
#    "max children reached":0,
#    "slow requests":0
# }


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
