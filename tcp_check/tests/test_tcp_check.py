# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy
import mock

from datadog_checks.tcp_check import TCPCheck

from . import common


def test_down(aggregator):
    """
    Service expected to be down
    """
    instance = deepcopy(common.INSTANCE_KO)
    instance['collect_response_time'] = True
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
    aggregator.assert_metric('network.tcp.response_time', count=0)  # should not submit response time metric on failure
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_reattempt_resolution():
    instance = deepcopy(common.INSTANCE)
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    def failed_connection(self):
        raise Exception()

    check.connect = failed_connection

    with mock.patch.object(check, 'resolve_ip', wraps=check.resolve_ip) as resolve_ip:
        check.check(instance)
        assert resolve_ip.called


def test_up(aggregator, check):
    """
    Service expected to be up
    """
    check.check(deepcopy(common.INSTANCE))
    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_response_time(aggregator):
    """
    Test the response time from a server expected to be up
    """
    instance = deepcopy(common.INSTANCE)
    instance['collect_response_time'] = True
    instance['name'] = 'instance:response_time'
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    # service check
    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:instance:response_time']
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1
