# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.tcp_check import TCPCheck
import pytest

CHECK_NAME = 'tcp_check'


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return TCPCheck(CHECK_NAME, {}, {})


@pytest.fixture
def instance_ko():
    return {
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService',
        'tags': ["foo:bar"],
    }


@pytest.fixture
def instance():
    return {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ["foo:bar"]
    }


def test_down(aggregator, check, instance_ko):
    """
    Service expected to be down
    """
    check.check(instance_ko)
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)


def test_up(aggregator, check, instance):
    """
    Service expected to be up
    """
    check.check(instance)
    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)


def test_response_time(aggregator, check, instance):
    """
    Test the response time from a server expected to be up
    """
    instance['collect_response_time'] = True
    instance['name'] = 'instance:response_time'
    check.check(instance)

    # service check
    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:instance:response_time']
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()
