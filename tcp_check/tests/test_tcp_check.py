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
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530", "foo:bar", "address:127.0.0.1"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
    aggregator.assert_metric('network.tcp.response_time', count=0)  # should not submit response time metric on failure
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_reattempt_resolution_on_error():
    instance = deepcopy(common.INSTANCE)
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    assert check.ip_cache_duration is None

    # IP is not normally re-resolved after the first check run
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert not resolve_ips.called

    # Upon connection failure, cached resolved IP is cleared
    with mock.patch.object(check, 'connect', wraps=check.connect) as connect:
        connect.side_effect = lambda self, addr: Exception()
        check.check(instance)
        assert check._addrs is None

    # On next check run IP is re-resolved
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert resolve_ips.called


def test_reattempt_resolution_on_duration():
    instance = deepcopy(common.INSTANCE)
    instance['ip_cache_duration'] = 0
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    assert check.ip_cache_duration is not None

    # ip_cache_duration = 0 means IP is re-resolved every check run
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert resolve_ips.called
        check.check(instance)
        assert resolve_ips.called
        check.check(instance)
        assert resolve_ips.called


def test_up(aggregator, check):
    """
    Service expected to be up
    """
    check.check(deepcopy(common.INSTANCE))
    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "foo:bar"]
    expected_tags.append("address:{}".format(check._addrs[0]))
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
    expected_tags.append("address:{}".format(check._addrs[0]))
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    expected_tags.append("address:{}".format(check._addrs[0]))
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_multiple(aggregator):
    """
    Test when a domain is attached to 3 IPs [UP, DOWN, UP]
    """
    instance = deepcopy(common.INSTANCE_MULTIPLE)
    instance['name'] = 'multiple'
    instance['ip_cache_duration'] = 0
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    with mock.patch('socket.gethostbyname_ex', return_value=[None, None, ['ip1', 'ip2', 'ip3']]), mock.patch.object(
        check, 'connect', wraps=check.connect
    ) as connect:
        connect.side_effect = [None, Exception(), None] * 2
        expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:multiple']

        # Running the check twice
        check.check(None)
        check.check(None)

        aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags + ['address:ip1'], count=2)
        aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags + ['address:ip2'], count=2)
        aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags + ['address:ip3'], count=2)
        aggregator.assert_service_check('tcp.can_connect', status=check.OK, count=4)
        aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, count=2)

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 6
