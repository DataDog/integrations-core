# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import platform

import pytest

from datadog_checks.dev.utils import ON_WINDOWS

if not ON_WINDOWS:
    pytest.skip('test_windows requires Windows', allow_module_level=True)

import ctypes
import socket
from collections import namedtuple

import mock

from datadog_checks.network.check_windows import TCPSTATS, WindowsNetwork

from . import common


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_creates_windows_instance(is_linux, is_bsd, is_solaris, is_windows, check):
    check_instance = check({})
    assert isinstance(check_instance, WindowsNetwork)


def test_get_tcp_stats_failure():
    if platform.system() == "Windows":
        instance = copy.deepcopy(common.INSTANCE)
        check_instance = WindowsNetwork('network', {}, [instance])

        with mock.patch(
            'datadog_checks.network.check_windows.Iphlpapi.GetTcpStatisticsEx', side_effect=ctypes.WinError()
        ), mock.patch.object(check_instance, 'submit_netmetric') as submit_netmetric:
            check_instance.check({})
            submit_netmetric.assert_not_called()


def test_get_tcp_stats(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance["collect_count_metrics"] = True
    check_instance = WindowsNetwork('network', {}, [instance])

    mock_stats = TCPSTATS(
        dwRtoAlgorithm=1,
        dwRtoMin=2,
        dwRtoMax=3,
        dwMaxConn=4,
        dwActiveOpens=5,
        dwPassiveOpens=6,
        dwAttemptFails=7,
        dwEstabResets=8,
        dwCurrEstab=9,
        dwInSegs=10,
        dwOutSegs=11,
        dwRetransSegs=12,
        dwInErrs=13,
        dwOutRsts=14,
        dwNumConns=15,
    )
    expected_mets = {
        'system.net.tcp4.active_opens': 5,
        'system.net.tcp4.passive_opens': 6,
        'system.net.tcp4.attempt_fails': 7,
        'system.net.tcp4.established_resets': 8,
        'system.net.tcp4.current_established': 9,
        'system.net.tcp4.in_segs': 10,
        'system.net.tcp4.out_segs': 11,
        'system.net.tcp4.retrans_segs': 12,
        'system.net.tcp4.in_errors': 13,
        'system.net.tcp4.out_resets': 14,
        'system.net.tcp4.connections': 15,
        'system.net.tcp6.active_opens': 5,
        'system.net.tcp6.passive_opens': 6,
        'system.net.tcp6.attempt_fails': 7,
        'system.net.tcp6.established_resets': 8,
        'system.net.tcp6.current_established': 9,
        'system.net.tcp6.in_segs': 10,
        'system.net.tcp6.out_segs': 11,
        'system.net.tcp6.retrans_segs': 12,
        'system.net.tcp6.in_errors': 13,
        'system.net.tcp6.out_resets': 14,
        'system.net.tcp6.connections': 15,
        'system.net.tcp.active_opens': 10,
        'system.net.tcp.passive_opens': 12,
        'system.net.tcp.attempt_fails': 14,
        'system.net.tcp.established_resets': 16,
        'system.net.tcp.current_established': 18,
        'system.net.tcp.in_segs': 20,
        'system.net.tcp.out_segs': 22,
        'system.net.tcp.retrans_segs': 24,
        'system.net.tcp.in_errors': 26,
        'system.net.tcp.out_resets': 28,
        'system.net.tcp.connections': 30,
    }
    gauge_mets = [
        'system.net.tcp4.connections',
        'system.net.tcp4.current_established',
        'system.net.tcp6.connections',
        'system.net.tcp6.current_established',
        'system.net.tcp.connections',
        'system.net.tcp.current_established',
    ]

    with mock.patch('datadog_checks.network.check_windows.WindowsNetwork._get_tcp_stats') as mock_get_tcp_stats:
        mock_get_tcp_stats.return_value = mock_stats  # Make _get_tcp_stats return my mock object
        check_instance.check({})
        for name, value in expected_mets.items():
            if name in gauge_mets:
                aggregator.assert_metric(name, value=value, metric_type=aggregator.GAUGE)
            else:
                aggregator.assert_metric(name, value=value, metric_type=aggregator.RATE)
                aggregator.assert_metric(name + '.count', value=value, metric_type=aggregator.MONOTONIC_COUNT)


def test_check_psutil_no_collect_connection_state(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = False
    check_instance = WindowsNetwork('network', {}, [instance])

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance.check({})

        _cx_state_psutil.assert_not_called()
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_check_psutil_collect_connection_state(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = WindowsNetwork('network', {}, [instance])

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance._collect_cx_state = True
        check_instance.check({})
        _cx_state_psutil.assert_called_once_with(tags=[])
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_cx_state_psutil(aggregator):
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

    check_instance = WindowsNetwork('network', {}, [common.INSTANCE])
    with mock.patch('datadog_checks.network.check_windows.psutil') as mock_psutil:
        mock_psutil.net_connections.return_value = conn
        check_instance._setup_metrics({})
        check_instance._cx_state_psutil()
        for m in aggregator._metrics.values():
            assert results[m[0].name] == m[0].value


def test_cx_counters_psutil(aggregator):
    snetio = namedtuple(
        'snetio', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv', 'errin', 'errout', 'dropin', 'dropout']
    )
    counters = {
        'Ethernet': snetio(
            bytes_sent=int(3096403230),
            bytes_recv=int(3280598526),
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
    check_instance = WindowsNetwork('network', {}, [instance])

    with mock.patch('datadog_checks.network.check_windows.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        check_instance._cx_counters_psutil()
        for m in aggregator._metrics.values():
            assert 'device:Ethernet' in m[0].tags
            if 'bytes_rcvd' in m[0].name:
                assert m[0].value == 3280598526


def test_parse_protocol_psutil(aggregator):
    conn = mock.MagicMock()
    check_instance = WindowsNetwork('network', {}, [common.INSTANCE])

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
