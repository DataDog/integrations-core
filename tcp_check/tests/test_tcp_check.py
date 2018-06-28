# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.tcp_check import TCPCheck
import pytest

RESULTS_TIMEOUT = 20

CONFIG = {
    'init_config': {},
    'instances': [{
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService'
    }, {
        'host': '126.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService2',
        'tags': ['test1']
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ['test2']
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1,
        'name': 'response_time',
        'tags': ['test3'],
        'collect_response_time': True
    }]
}

CHECK_NAME = 'tcp_check'


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def test_check(aggregator):
    """
    Check coverage.
    """
    check = TCPCheck(CHECK_NAME, {}, {})
    # Run the check
    for instance in CONFIG["instances"]:
        check.check(instance)
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)

    expected_tags = ["instance:DownService2", "target_host:126.0.0.1", "port:65530", "test1"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)

    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "test2"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)

    expected_tags = ["instance:response_time", "target_host:datadoghq.com", "port:80", "test3"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)

    expected_tags = ["instance:response_time", "url:datadoghq.com:80", "test3"]
    aggregator.assert_metric('network.tcp.response_time', status=check.OK, tags=expected_tags)

    aggregator.assert_all_metrics_covered()
