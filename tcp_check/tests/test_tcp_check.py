# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import platform
import re
import socket
from collections import namedtuple
from copy import deepcopy

import mock
import pytest

from datadog_checks.tcp_check import TCPCheck

from . import common

addr_tuple = namedtuple('addr_tuple', ['address', 'socket_type'])


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
        connect.side_effect = lambda self, addr, socket_type: Exception()
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
    expected_tags.append("address:{}".format(check._addrs[0].address))
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
    expected_tags.append("address:{}".format(check._addrs[0].address))
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    expected_tags.append("address:{}".format(check._addrs[0].address))
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


@pytest.mark.parametrize(
    'hostname, getaddrinfo, expected_addrs, multiple_ips, service_checks_count',
    [
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV6,
            [addr_tuple('::1', socket.AF_INET6)],
            False,
            1,
            id='Dual IPv4/IPv6: localhost, IPv6 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [addr_tuple('127.0.0.1', socket.AF_INET)],
            False,
            1,
            id='Dual IPv4/IPv6: localhost, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV6,
            [addr_tuple('::1', socket.AF_INET6), addr_tuple('127.0.0.1', socket.AF_INET)],
            True,
            2,
            id='Dual IPv4/IPv6: localhost, IPv6 resolution, multiple_ips True',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [addr_tuple('127.0.0.1', socket.AF_INET), addr_tuple('::1', socket.AF_INET6)],
            True,
            2,
            id='Dual IPv4/IPv6: localhost, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'some-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4,
            [addr_tuple('ip1', socket.AF_INET)],
            False,
            1,
            id='Dual IPv4/IPv6: string hostname, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV6,
            [addr_tuple('ip1', socket.AF_INET6)],
            False,
            1,
            id='Dual IPv4/IPv6: string hostname, IPv6 resolution, multiple_ips False',
        ),
        pytest.param(
            'some-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4,
            [addr_tuple('ip1', socket.AF_INET), addr_tuple('ip2', socket.AF_INET6), addr_tuple('ip3', socket.AF_INET6)],
            True,
            3,
            id='Dual IPv4/IPv6: string hostname, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV6,
            [addr_tuple('ip1', socket.AF_INET6), addr_tuple('ip2', socket.AF_INET), addr_tuple('ip3', socket.AF_INET6)],
            True,
            3,
            id='Dual IPv4/IPv6: string hostname, IPv6 resolution, multiple_ips True',
        ),
        pytest.param(
            'localhost',
            common.SINGLE_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [addr_tuple('127.0.0.1', socket.AF_INET)],
            False,
            1,
            id='Single stack IPv4: localhost, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.SINGLE_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [addr_tuple('127.0.0.1', socket.AF_INET), addr_tuple('ip2', socket.AF_INET)],
            True,
            2,
            id='Single stack IPv4: localhost, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.SINGLE_STACK_GETADDRINFO_IPV4,
            [addr_tuple('ip1', socket.AF_INET)],
            False,
            1,
            id='Single stack IPv4: string hostname, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'another-hostname',
            common.SINGLE_STACK_GETADDRINFO_IPV4,
            [addr_tuple('ip1', socket.AF_INET), addr_tuple('ip2', socket.AF_INET), addr_tuple('ip3', socket.AF_INET)],
            True,
            3,
            id='Single stack IPv4: string hostname, IPv4 resolution, multiple_ips True',
        ),
    ],
)
def test_hostname_resolution(
    aggregator, monkeypatch, hostname, getaddrinfo, expected_addrs, multiple_ips, service_checks_count
):
    """
    Test that string hostnames get resolved to ipv4 address format properly.
    """
    instance = deepcopy(common.INSTANCE)
    instance['host'] = hostname
    instance['multiple_ips'] = multiple_ips
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    monkeypatch.setattr('socket.getaddrinfo', mock.Mock(return_value=getaddrinfo))
    monkeypatch.setattr(check, 'connect', mock.Mock(side_effect=[None, None, None]))

    expected_tags = [
        "instance:UpService",
        "target_host:{}".format(hostname),
        "port:80",
        "foo:bar",
        "address:{}".format(expected_addrs[0].address),
    ]

    check.check(instance)

    assert check._addrs == expected_addrs
    # at the end of check.check() run, check.socket_type will be assigned to the last addr's socket type
    assert check.socket_type == expected_addrs[-1:][0].socket_type

    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags, count=1)
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags, count=1)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == service_checks_count


def test_multiple(aggregator):
    """
    Test when a domain is attached to 3 IPs [UP, DOWN, UP]
    """
    instance = deepcopy(common.INSTANCE_MULTIPLE)
    instance['name'] = 'multiple'
    instance['ip_cache_duration'] = 0
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    with mock.patch(
        'socket.getaddrinfo',
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('ip1', 80)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('ip2', 80, 0, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('ip3', 80, 0, 0)),
        ],
    ), mock.patch.object(check, 'connect', wraps=check.connect) as connect:
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


def has_ipv6_connectivity():
    try:
        for sockaddr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6, 0, socket.IPPROTO_TCP):
            if not sockaddr[0].startswith('fe80:'):
                return True
        return False
    except socket.gaierror:
        return False


def test_ipv6(aggregator, check):
    """
    Service expected to be up
    """
    instance = deepcopy(common.INSTANCE_IPV6)
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    nb_ipv4, nb_ipv6 = 0, 0
    for addr in check.addrs:
        expected_tags = ["instance:UpService", "target_host:ip-ranges.datadoghq.com", "port:80", "foo:bar"]
        expected_tags.append("address:{}".format(addr.address))
        if re.match(r'^[0-9a-f:]+$', addr.address):
            nb_ipv6 += 1
            if has_ipv6_connectivity():
                aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
            elif platform.system() == 'Darwin':
                # IPv6 connectivity varies when running test locally on macOS, so we do not check status or metric value
                aggregator.assert_service_check('tcp.can_connect', tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', tags=expected_tags)
            else:
                aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
        else:
            nb_ipv4 += 1
            aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
            aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    assert nb_ipv4 == 4
    # The Windows CI machine doesn't return IPv6
    # Windows or MacOS might not have IPv6 connectivity when testing locally
    assert (
        nb_ipv6 == 8
        or platform.system() == 'Windows'
        and nb_ipv6 == 0
        or platform.system() == 'Darwin'
        and nb_ipv6 == 0
    )
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == nb_ipv4 + nb_ipv6
