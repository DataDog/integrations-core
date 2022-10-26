# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import socket
from collections import namedtuple

import mock
from six import PY3, iteritems

from datadog_checks.network.check_windows import WindowsNetwork

from . import common

if PY3:
    long = int


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_creates_windows_instance(is_linux, is_bsd, is_solaris, is_windows, check):
    check_instance = check({})
    assert isinstance(check_instance, WindowsNetwork)


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
        for _, m in iteritems(aggregator._metrics):
            assert results[m[0].name] == m[0].value


def test_cx_counters_psutil(aggregator):
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
    check_instance = WindowsNetwork('network', {}, [instance])

    with mock.patch('datadog_checks.network.check_windows.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        check_instance._cx_counters_psutil()
        for _, m in iteritems(aggregator._metrics):
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
