# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import logging
import os

import mock
import pytest
from six import PY3, iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import get_subprocess_output
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.network.check_linux import LinuxNetwork

from . import common
from .common import FIXTURE_DIR, decode_string

LINUX_SYS_NET_STATS = {
    'system.net.iface.mtu': (65536, 9001),
    'system.net.iface.tx_queue_len': (1000, 1000),
    'system.net.iface.num_rx_queues': (1, 2),
    'system.net.iface.num_tx_queues': (1, 3),
}

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


CONNECTION_QUEUES_METRICS = ['system.net.tcp.recv_q', 'system.net.tcp.send_q']


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


def ss_subprocess_mock_fails(*args, **kwargs):
    if args[0][2].startswith('ss '):
        raise OSError('boom')
    else:
        return get_subprocess_output(*args, **kwargs)


def netstat_subprocess_mock(*args, **kwargs):
    if args[0][0] == 'sh':
        raise OSError()
    elif args[0][0] == 'netstat':
        with open(os.path.join(FIXTURE_DIR, 'netstat'), 'rb') as f:
            contents = f.read()
            return decode_string(contents), None, None


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


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_returns_the_right_instance(is_linux, check):
    check_instance = check({})
    assert isinstance(check_instance, LinuxNetwork)


@pytest.mark.skipif(not Platform.is_linux(), reason="Only works on Linux systems")
def test_collect_cx_queues(check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_queues'] = True
    instance['collect_connection_state'] = True
    check_instance = LinuxNetwork('network', {}, [instance])

    check_instance.check({})

    for metric in CONNECTION_QUEUES_METRICS + common.EXPECTED_METRICS + common.EXPECTED_WINDOWS_LINUX_METRICS:
        aggregator.assert_metric(metric)

    # TODO Add this assert back when `assert_metrics_using_metadata` properly handles histograms
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(not Platform.is_linux(), reason="Only works on Linux systems")
def test_collect_cx_queues_when_ss_fails(check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_queues'] = True
    instance['collect_connection_state'] = True
    check_instance = LinuxNetwork('network', {}, [instance])
    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock_fails
        check_instance.check({})

    for metric in CONNECTION_QUEUES_METRICS + common.EXPECTED_METRICS + common.EXPECTED_WINDOWS_LINUX_METRICS:
        aggregator.assert_metric(metric)

    # TODO Add this assert back when `assert_metrics_using_metadata` properly handles histograms
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(Platform.is_windows(), reason="Only runs on Unix systems")
def test_cx_state(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = LinuxNetwork('network', {}, [instance])

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

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(Platform.is_windows(), reason="Only runs on Unix systems")
@mock.patch('os.listdir', side_effect=os_list_dir_mock)
@mock.patch('datadog_checks.network.check_linux.LinuxNetwork._read_int_file', side_effect=read_int_file_mock)
def test_linux_sys_net(listdir, read_int_file, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    check_instance = LinuxNetwork('network', {}, [instance])

    check_instance.check({})

    for metric, value in iteritems(LINUX_SYS_NET_STATS):
        aggregator.assert_metric(metric, value=value[0], tags=['iface:lo'])
        aggregator.assert_metric(metric, value=value[1], tags=['iface:ens5'])

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_cx_state_mocked(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = LinuxNetwork('network', {}, [instance])
    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
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

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_add_conntrack_stats_metrics(aggregator):
    mocked_conntrack_stats = (
        "cpu=0 found=27644 invalid=19060 ignore=485633411 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=39936711\n"
        "cpu=1 found=21960 invalid=17288 ignore=475938848 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=36983181"
    )
    check_instance = LinuxNetwork('network', {}, [{}])
    with mock.patch('datadog_checks.network.check_linux.get_subprocess_output') as subprocess:
        subprocess.return_value = mocked_conntrack_stats, None, None
        check_instance._add_conntrack_stats_metrics(None, None, ['foo:bar'])

        for metric, value in iteritems(CONNTRACK_STATS):
            aggregator.assert_metric(metric, value=value[0], tags=['foo:bar', 'cpu:0'])
            aggregator.assert_metric(metric, value=value[1], tags=['foo:bar', 'cpu:1'])

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(not PY3, reason="mock builtins only works on Python 3")
def test_proc_permissions_error(aggregator, caplog):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = False
    check_instance = LinuxNetwork('network', {}, [instance])
    caplog.set_level(logging.DEBUG)

    with mock.patch('builtins.open', mock.mock_open()) as mock_file:
        mock_file.side_effect = IOError()
        # force linux check so it will run on macOS too
        check_instance.check(instance)
        assert 'Unable to read /proc/net/dev.' in caplog.text
        assert 'Unable to read /proc/net/netstat.' in caplog.text
        assert 'Unable to read /proc/net/snmp.' in caplog.text


@mock.patch('datadog_checks.network.network.find_executable', return_value='/bin/ss')
def test_ss_with_custom_procfs(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = LinuxNetwork('network', {}, [instance])
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


def test_proc_net_metrics(aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_count_metrics'] = True
    check_instance = LinuxNetwork('network', {}, [instance])
    check_instance.get_net_proc_base_location = lambda x: FIXTURE_DIR

    check_instance.check({})
    for metric, value in iteritems(PROC_NET_STATS):
        aggregator.assert_metric(metric, value=value)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
