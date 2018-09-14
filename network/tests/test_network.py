# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import namedtuple
import socket
import os
import platform

# project
from datadog_checks.network import Network

import mock
import pytest

FIXTURE_DIR = os.path.dirname(__file__)

CX_STATE_GAUGES_VALUES = {
    'system.net.udp4.connections': 2,
    'system.net.udp6.connections': 3,
    'system.net.tcp4.established': 1,
    'system.net.tcp4.opening': 0,
    'system.net.tcp4.closing': 0,
    'system.net.tcp4.listening': 2,
    'system.net.tcp4.time_wait': 2,
    'system.net.tcp6.established': 1,
    'system.net.tcp6.opening': 0,
    'system.net.tcp6.closing': 1,
    'system.net.tcp6.listening': 1,
    'system.net.tcp6.time_wait': 1,
}

network_check = Network('network', {}, {})


@pytest.fixture
def ss_subprocess_mock(*args, **kwargs):
    if args[0][-1] == '-4' and args[0][-3] == '-u':
        file_name = 'ss_ipv4_udp'
    elif args[0][-1] == '-4' and args[0][-3] == '-t':
        file_name = 'ss_ipv4_tcp'
    elif args[0][-1] == '-6' and args[0][-3] == '-u':
        file_name = 'ss_ipv6_udp'
    elif args[0][-1] == '-6' and args[0][-3] == '-t':
        file_name = 'ss_ipv6_tcp'

    with open(file_name, FIXTURE_DIR) as f:
        contents = f.read()
        contents = contents.decode('string-escape')
        return contents.decode("utf-8")


@pytest.fixture
def netstat_subprocess_mock(*args, **kwargs):
    if args[0][0] == 'ss':
        raise OSError
    elif args[0][0] == 'netstat':
        with open('netstat', FIXTURE_DIR) as f:
            contents = f.read()
            contents = contents.decode('string-escape')
            return contents.decode("utf-8")


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.mark.skipif(platform.system() is not 'Linux',
                    reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.get_subprocess_output', side_effect=ss_subprocess_mock)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_cx_state_linux_ss(mock_is_linux, mock_get_subprocess_output, aggregator):
    network_check.check({})

    # Assert metrics
    for metric, value in CX_STATE_GAUGES_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=['optional:tag1'])


@pytest.mark.skipif(platform.system() is not 'Linux',
                    reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.get_subprocess_output', side_effect=netstat_subprocess_mock)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_cx_state_linux_netstat(mock_is_linux, mock_get_subprocess_output, aggregator):
    network_check.run_check({})

    # Assert metrics
    for metric, value in CX_STATE_GAUGES_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=['optional:tag1'])


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_win_uses_psutil(*args):
        with mock.patch.object(network_check, '_check_psutil') as _check_psutil:
            network_check.check({})
            network_check._check_psutil = mock.MagicMock()
            _check_psutil.assert_called_once_with({})


def test_check_psutil(aggregator):
    with mock.patch.object(network_check, '_cx_state_psutil') as _cx_state_psutil, \
            mock.patch.object(network_check, '_cx_counters_psutil') as _cx_counters_psutil:
        network_check._collect_cx_state = False
        network_check._check_psutil({})
        _cx_state_psutil.assert_not_called()
        _cx_counters_psutil.assert_called_once_with(tags=[])

    with mock.patch.object(network_check, '_cx_state_psutil') as _cx_state_psutil, \
            mock.patch.object(network_check, '_cx_counters_psutil') as _cx_counters_psutil:
        network_check._collect_cx_state = True
        network_check._check_psutil({})
        _cx_state_psutil.assert_called_once_with(tags=[])
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_cx_state_psutil(aggregator):
    sconn = namedtuple(
        'sconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status', 'pid'])
    conn = [
        sconn(
            fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 50482), raddr=('127.0.0.1', 2638),
            status='ESTABLISHED', pid=1416
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM,
            laddr=('::', 50482), raddr=('::', 2638),
            status='ESTABLISHED', pid=42
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM,
            laddr=('::', 49163), raddr=(),
            status='LISTEN', pid=1416
        ),
        sconn(
            fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM,
            laddr=('0.0.0.0', 445), raddr=(),
            status='LISTEN', pid=4
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM,
            laddr=('::1', 56521), raddr=('::1', 17123),
            status='TIME_WAIT', pid=0
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_DGRAM,
            laddr=('::', 500), raddr=(), status='NONE', pid=892
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM,
            laddr=('::1', 56493), raddr=('::1', 17123),
            status='TIME_WAIT', pid=0
        ),
        sconn(
            fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 54541), raddr=('127.0.0.1', 54542),
            status='ESTABLISHED', pid=20500
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

    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
        mock_psutil.net_connections.return_value = conn
        network_check._cx_state_psutil()
        for _, m in aggregator._metrics.iteritems():
            assert results[m[0].name] == m[0].value


def test_cx_counters_psutil(aggregator):
    snetio = namedtuple(
        'snetio',
        ['bytes_sent', 'bytes_recv', 'packets_sent',
         'packets_recv', 'errin', 'errout',
         'dropin', 'dropout']
    )
    counters = {
        'Ethernet':
        snetio(
            bytes_sent=3096403230L, bytes_recv=3280598526L,
            packets_sent=6777924, packets_recv=32888147,
            errin=0, errout=0, dropin=0, dropout=0),
        'Loopback Pseudo-Interface 1':
        snetio(
            bytes_sent=0, bytes_recv=0,
            packets_sent=0, packets_recv=0, errin=0,
            errout=0, dropin=0, dropout=0),
    }
    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        network_check._excluded_ifaces = ['Loopback Pseudo-Interface 1']
        network_check._exclude_iface_re = ''
        network_check._cx_counters_psutil()
        for _, m in aggregator._metrics.iteritems():
            assert 'device:Ethernet' in m[0].tags
            if 'bytes_rcvd' in m[0].name:
                print m
                assert m[0].value == 3280598526


def test_parse_protocol_psutil(aggregator):
    import socket
    conn = mock.MagicMock()

    protocol = network_check._parse_protocol_psutil(conn)
    assert protocol == ''

    conn.type = socket.SOCK_STREAM
    conn.family = socket.AF_INET6
    protocol = network_check._parse_protocol_psutil(conn)
    assert protocol == 'tcp6'

    conn.type = socket.SOCK_DGRAM
    conn.family = socket.AF_INET
    protocol = network_check._parse_protocol_psutil(conn)
    assert protocol == 'udp4'
