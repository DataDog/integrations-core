# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import socket
from collections import namedtuple

import mock
import pytest
from six import PY3, iteritems

from datadog_checks.dev import EnvVars

from . import common

if PY3:
    long = int


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_check_psutil_no_collect_connection_state(is_windows, is_linux, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = False
    check_instance = check(instance)

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance.check({})

        _cx_state_psutil.assert_not_called()
        _cx_counters_psutil.assert_called_once_with(tags=[])


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_check_psutil_collect_connection_state(is_windows, is_linux, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance._collect_cx_state = True
        check_instance.check({})
        _cx_state_psutil.assert_called_once_with(tags=[])
        _cx_counters_psutil.assert_called_once_with(tags=[])


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_cx_state_psutil(is_windows, is_linux, aggregator, check):
    sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status', 'pid'])
    conn = [
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 50482),
            raddr=('127.0.0.1', 2638),
            status='ESTABLISHED',
            pid=1416,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::', 50482),
            raddr=('::', 2638),
            status='ESTABLISHED',
            pid=42,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::', 49163),
            raddr=(),
            status='LISTEN',
            pid=1416,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('0.0.0.0', 445),
            raddr=(),
            status='LISTEN',
            pid=4,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::1', 56521),
            raddr=('::1', 17123),
            status='TIME_WAIT',
            pid=0,
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_DGRAM, laddr=('::', 500), raddr=(), status='NONE', pid=892
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::1', 56493),
            raddr=('::1', 17123),
            status='TIME_WAIT',
            pid=0,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 54541),
            raddr=('127.0.0.1', 54542),
            status='ESTABLISHED',
            pid=20500,
        ),
    ]

    results = {
        'system.net.tcp6.time_wait': 2,
        'system.net.tcp4.listening': 1,
        'system.net.tcp6.closing': 0,
        'system.net.tcp4.closing': 0,
        'system.net.tcp4.time_wait': 0,
        'system.net.tcp6.established': 1,
        'system.net.tcp4.established': 2,
        'system.net.tcp6.listening': 1,
        'system.net.tcp4.opening': 0,
        'system.net.udp4.connections': 0,
        'system.net.udp6.connections': 1,
        'system.net.tcp6.opening': 0,
    }

    check_instance = check(common.INSTANCE)
    with mock.patch('datadog_checks.network.check_windows.psutil') as mock_psutil:
        mock_psutil.net_connections.return_value = conn
        check_instance._setup_metrics({})
        check_instance._cx_state_psutil()
        for _, m in iteritems(aggregator._metrics):
            assert results[m[0].name] == m[0].value


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_cx_counters_psutil(is_linux, is_bsd, is_windows, aggregator, check):
    snetio = namedtuple(
        'snetio', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv', 'errin', 'errout', 'dropin', 'dropout']
    )
    counters = {
        'Ethernet': snetio(
            bytes_sent=long(3096403230),
            bytes_recv=long(3280598526),
            packets_sent=6777924,
            packets_recv=32888147,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        ),
        'Loopback Pseudo-Interface 1': snetio(
            bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0, errin=0, errout=0, dropin=0, dropout=0
        ),
    }

    instance = copy.deepcopy(common.INSTANCE)
    instance['excluded_interfaces'] = ['Loopback Pseudo-Interface 1']
    instance['excluded_interface_re'] = ''
    check_instance = check(instance)

    with mock.patch('datadog_checks.network.check_windows.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        check_instance._cx_counters_psutil()
        for _, m in iteritems(aggregator._metrics):
            assert 'device:Ethernet' in m[0].tags
            if 'bytes_rcvd' in m[0].name:
                assert m[0].value == 3280598526


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_parse_protocol_psutil(is_windows, is_linux, aggregator, check):
    import socket

    conn = mock.MagicMock()
    check_instance = check(common.INSTANCE)

    protocol = check_instance._parse_protocol_psutil(conn)
    assert protocol == ''

    conn.type = socket.SOCK_STREAM
    conn.family = socket.AF_INET6
    protocol = check_instance._parse_protocol_psutil(conn)
    assert protocol == 'tcp6'

    conn.type = socket.SOCK_DGRAM
    conn.family = socket.AF_INET
    protocol = check_instance._parse_protocol_psutil(conn)
    assert protocol == 'udp4'


@pytest.mark.parametrize(
    "proc_location, envs, expected_net_proc_base_location",
    [
        ("/something/proc", {'DOCKER_DD_AGENT': 'true'}, "/something/proc/1"),
        ("/something/proc", {}, "/something/proc"),
        ("/proc", {'DOCKER_DD_AGENT': 'true'}, "/proc"),
        ("/proc", {}, "/proc"),
    ],
)
def test_get_net_proc_base_location(aggregator, check, proc_location, envs, expected_net_proc_base_location):
    check_instance = check(common.INSTANCE)
    with EnvVars(envs):
        actual = check_instance.get_net_proc_base_location(proc_location)
        assert expected_net_proc_base_location == actual


def test_invalid_excluded_interfaces(check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['excluded_interfaces'] = None
    check_instance = check(instance)
    result = check_instance.run()
    assert 'ConfigurationError' in result
    assert "Expected 'excluded_interfaces' to be a list, got 'NoneType'" in result


@pytest.mark.parametrize(
    "proc_location, ss_found, expected",
    [("/proc", False, True), ("/something/proc", False, False), ("/something/proc", True, True)],
)
def test_is_collect_cx_state_runnable(aggregator, check, proc_location, ss_found, expected):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)
    with mock.patch('distutils.spawn.find_executable', lambda x: "/bin/ss" if ss_found else None):
        assert check_instance.is_collect_cx_state_runnable(proc_location) == expected
