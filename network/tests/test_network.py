# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import logging
import os
import socket
from collections import namedtuple

import mock
import pytest
from six import PY3, iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev import EnvVars

from . import common

if PY3:
    long = int

FIXTURE_DIR = os.path.join(common.HERE, 'fixtures')

CX_STATE_GAUGES_VALUES = {
    'system.net.udp4.connections': 2,
    'system.net.udp6.connections': 3,
    'system.net.tcp4.established': 1,
    'system.net.tcp4.opening': 2,
    'system.net.tcp4.closing': 2,
    'system.net.tcp4.listening': 2,
    'system.net.tcp4.time_wait': 2,
    'system.net.tcp6.established': 1,
    'system.net.tcp6.opening': 0,
    'system.net.tcp6.closing': 1,
    'system.net.tcp6.listening': 1,
    'system.net.tcp6.time_wait': 1,
}

CONNTRACK_STATS = {
    'system.net.conntrack.found': (27644, 21960),
    'system.net.conntrack.invalid': (19060, 17288),
    'system.net.conntrack.ignore': (485633411, 475938848),
    'system.net.conntrack.insert': (0, 0),
    'system.net.conntrack.insert_failed': (1, 1),
    'system.net.conntrack.drop': (1, 1),
    'system.net.conntrack.early_drop': (0, 0),
    'system.net.conntrack.error': (0, 0),
    'system.net.conntrack.search_restart': (39936711, 36983181),
}

LINUX_SYS_NET_STATS = {
    'system.net.iface.mtu': (65536, 9001),
    'system.net.iface.tx_queue_len': (1000, 1000),
    'system.net.iface.num_rx_queues': (1, 2),
    'system.net.iface.num_tx_queues': (1, 3),
}

PROC_NET_STATS = {
    'system.net.ip.in_receives': 159747123,
    'system.net.ip.in_header_errors': 23,
    'system.net.ip.in_addr_errors': 0,
    'system.net.ip.in_unknown_protos': 0,
    'system.net.ip.in_discards': 0,
    'system.net.ip.in_delivers': 159745645,
    'system.net.ip.out_requests': 162992767,
    'system.net.ip.out_discards': 613,
    'system.net.ip.out_no_routes': 0,
    'system.net.ip.forwarded_datagrams': 1449,
    'system.net.ip.reassembly_timeouts': 0,
    'system.net.ip.reassembly_requests': 0,
    'system.net.ip.reassembly_oks': 0,
    'system.net.ip.reassembly_fails': 0,
    'system.net.ip.fragmentation_oks': 0,
    'system.net.ip.fragmentation_fails': 0,
    'system.net.ip.fragmentation_creates': 0,
    'system.net.ip.in_receives.count': 159747123,
    'system.net.ip.in_header_errors.count': 23,
    'system.net.ip.in_addr_errors.count': 0,
    'system.net.ip.in_unknown_protos.count': 0,
    'system.net.ip.in_discards.count': 0,
    'system.net.ip.in_delivers.count': 159745645,
    'system.net.ip.out_requests.count': 162992767,
    'system.net.ip.out_discards.count': 613,
    'system.net.ip.out_no_routes.count': 0,
    'system.net.ip.forwarded_datagrams.count': 1449,
    'system.net.ip.reassembly_timeouts.count': 0,
    'system.net.ip.reassembly_requests.count': 0,
    'system.net.ip.reassembly_oks.count': 0,
    'system.net.ip.reassembly_fails.count': 0,
    'system.net.ip.fragmentation_oks.count': 0,
    'system.net.ip.fragmentation_fails.count': 0,
    'system.net.ip.fragmentation_creates.count': 0,
    'system.net.tcp.active_opens': 6828054,
    'system.net.tcp.passive_opens': 4198200,
    'system.net.tcp.attempt_fails': 174,
    'system.net.tcp.established_resets': 761431,
    'system.net.tcp.current_established': 59,
    'system.net.tcp.in_errors': 0,
    'system.net.tcp.out_resets': 792992,
    'system.net.tcp.in_csum_errors': 0,
    'system.net.tcp.active_opens.count': 6828054,
    'system.net.tcp.passive_opens.count': 4198200,
    'system.net.tcp.attempt_fails.count': 174,
    'system.net.tcp.established_resets.count': 761431,
    'system.net.tcp.in_errors.count': 0,
    'system.net.tcp.out_resets.count': 792992,
    'system.net.tcp.in_csum_errors.count': 0,
    'system.net.ip.in_no_routes': 6,
    'system.net.ip.in_truncated_pkts': 0,
    'system.net.ip.in_csum_errors': 0,
    'system.net.ip.reassembly_overlaps': 0,
    'system.net.ip.in_no_routes.count': 6,
    'system.net.ip.in_truncated_pkts.count': 0,
    'system.net.ip.in_csum_errors.count': 0,
    'system.net.ip.reassembly_overlaps.count': 0,
}

if PY3:
    ESCAPE_ENCODING = 'unicode-escape'

    def decode_string(s):
        return s.decode(ESCAPE_ENCODING)

else:
    ESCAPE_ENCODING = 'string-escape'

    def decode_string(s):
        s.decode(ESCAPE_ENCODING)
        return s.decode("utf-8")


def read_int_file_mock(location):
    if location == '/sys/class/net/lo/mtu':
        return 65536
    elif location == '/sys/class/net/lo/tx_queue_len':
        return 1000
    elif location == '/sys/class/net/ens5/mtu':
        return 9001
    elif location == '/sys/class/net/ens5/tx_queue_len':
        return 1000
    elif location == '/sys/class/net/invalid/mtu':
        return None
    elif location == '/sys/class/net/invalid/tx_queue_len':
        return None


def os_list_dir_mock(location):
    if location == '/sys/class/net':
        return ['ens5', 'lo', 'invalid']
    elif location == '/sys/class/net/lo/queues':
        return ['rx-1', 'tx-1']
    elif location == '/sys/class/net/ens5/queues':
        return ['rx-1', 'rx-2', 'tx-1', 'tx-2', 'tx-3']
    elif location == '/sys/class/net/invalid/queues':
        raise OSError()


def ss_subprocess_mock(*args, **kwargs):
    if '--udp --all --ipv4' in args[0][2]:
        return '3', None, None
    elif '--udp --all --ipv6' in args[0][2]:
        return '4', None, None
    elif '--tcp --all --ipv4' in args[0][2]:
        file_name = 'ss_ipv4_tcp_short'
    elif '--tcp --all --ipv6' in args[0][2]:
        file_name = 'ss_ipv6_tcp_short'

    with open(os.path.join(FIXTURE_DIR, file_name), 'rb') as f:
        contents = f.read()
        return decode_string(contents), None, None


def netstat_subprocess_mock(*args, **kwargs):
    if args[0][0] == 'sh':
        raise OSError()
    elif args[0][0] == 'netstat':
        with open(os.path.join(FIXTURE_DIR, 'netstat'), 'rb') as f:
            contents = f.read()
            return decode_string(contents), None, None


@pytest.mark.skipif(Platform.is_windows(), reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_cx_state(is_bds, is_linux, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)

    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check_instance.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)
        aggregator.reset()

        out.side_effect = netstat_subprocess_mock
        check_instance.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)


@pytest.mark.skipif(Platform.is_windows(), reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
@mock.patch('os.listdir', side_effect=os_list_dir_mock)
@mock.patch('datadog_checks.network.check_linux.LinuxNetwork._read_int_file', side_effect=read_int_file_mock)
def test_linux_sys_net(is_linux, listdir, read_int_file, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    check_instance = check(instance)

    check_instance.check({})

    for metric, value in iteritems(LINUX_SYS_NET_STATS):
        aggregator.assert_metric(metric, value=value[0], tags=['iface:lo'])
        aggregator.assert_metric(metric, value=value[1], tags=['iface:ens5'])
    aggregator.reset()


@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_cx_state_mocked(is_bsd, is_linux, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)
    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check_instance._get_linux_sys_net = lambda x: True
        check_instance.is_collect_cx_state_runnable = lambda x: True
        check_instance.get_net_proc_base_location = lambda x: FIXTURE_DIR

        check_instance.check({})
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)

        aggregator.reset()
        out.side_effect = netstat_subprocess_mock
        check_instance.check({})
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_proc_net_metrics(is_linux, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_count_metrics'] = True
    check_instance = check(instance)
    check_instance.get_net_proc_base_location = lambda x: FIXTURE_DIR

    check_instance.check({})
    for metric, value in iteritems(PROC_NET_STATS):
        aggregator.assert_metric(metric, value=value)


@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_add_conntrack_stats_metrics(is_linux, is_bsd, aggregator, check):
    mocked_conntrack_stats = (
        "cpu=0 found=27644 invalid=19060 ignore=485633411 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=39936711\n"
        "cpu=1 found=21960 invalid=17288 ignore=475938848 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=36983181"
    )
    check_instance = check({})
    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as subprocess:
        subprocess.return_value = mocked_conntrack_stats, None, None
        check_instance._add_conntrack_stats_metrics(None, None, ['foo:bar'])

        for metric, value in iteritems(CONNTRACK_STATS):
            aggregator.assert_metric(metric, value=value[0], tags=['foo:bar', 'cpu:0'])
            aggregator.assert_metric(metric, value=value[1], tags=['foo:bar', 'cpu:1'])


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_win_uses_psutil(is_linux, is_bsd, is_solaris, is_windows, check):
    check_instance = check({})
    with mock.patch.object(check_instance, '_check_psutil') as _check_psutil:
        check_instance.check({})
        check._check_psutil = mock.MagicMock()
        _check_psutil.assert_called_once_with({})


def test_check_psutil_no_collect_connection_state(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = False
    check_instance = check(instance)

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance._check_psutil({})

        _cx_state_psutil.assert_not_called()
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_check_psutil_collect_connection_state(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)

    with mock.patch.object(check_instance, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check_instance, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check_instance._collect_cx_state = True
        check_instance._check_psutil({})
        _cx_state_psutil.assert_called_once_with(tags=[])
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_cx_state_psutil(aggregator, check):
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
    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
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

    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        check_instance._cx_counters_psutil()
        for _, m in iteritems(aggregator._metrics):
            assert 'device:Ethernet' in m[0].tags
            if 'bytes_rcvd' in m[0].name:
                assert m[0].value == 3280598526


def test_parse_protocol_psutil(aggregator, check):
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


@pytest.mark.skipif(not PY3, reason="mock builtins only works on Python 3")
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_proc_permissions_error(is_bsd, is_linux, aggregator, check, caplog):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = False
    check_instance = check(instance)
    caplog.set_level(logging.DEBUG)

    with mock.patch('builtins.open', mock.mock_open()) as mock_file:
        mock_file.side_effect = IOError()
        # force linux check so it will run on macOS too
        check_instance.check(instance)
        assert 'Unable to read /proc/net/dev.' in caplog.text
        assert 'Unable to read /proc/net/netstat.' in caplog.text
        assert 'Unable to read /proc/net/snmp.' in caplog.text


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


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=False)
@mock.patch('distutils.spawn.find_executable', return_value='/bin/ss')
def test_ss_with_custom_procfs(is_linux, is_bsd, is_solaris, is_windows, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)
    check_instance._get_linux_sys_net = lambda x: True
    with mock.patch(
        'datadog_checks.network.check_linux.get_subprocess_output', side_effect=ss_subprocess_mock
    ) as get_subprocess_output:
        check_instance.get_net_proc_base_location = lambda x: "/something/proc"
        check_instance.check({})
        get_subprocess_output.assert_called_with(
            ["sh", "-c", "ss --numeric --udp --all --ipv6 | wc -l"],
            check_instance.log,
            env={'PROC_ROOT': "/something/proc", 'PATH': os.environ["PATH"]},
        )
