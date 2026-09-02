# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.powerha import PowerhaCheck
from datadog_checks.powerha import parsers

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def read_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


UTILITIES_PATH = '/usr/es/sbin/cluster/utilities'
CLRAS_PATH = '/usr/lib/cluster/clras'

# argv (as a tuple) -> fixture file name, for the "everything healthy, unicast,
# stable cluster manager" scenario.
HAPPY_PATH_DISPATCH = {
    ('odmget', 'HACMPcluster'): 'odmget_hacmpcluster.txt',
    ('odmget', 'HACMPnode'): 'odmget_hacmpnode.txt',
    ('lslpp', '-Lc', 'cluster.es.server.rte'): 'lslpp_lc_cluster_es_server_rte.txt',
    ('lssrc', '-ls', 'clstrmgrES'): 'lssrc_clstrmgres_stable.txt',
    ('lscluster', '-m'): 'lscluster_m_unicast.txt',
    (os.path.join(UTILITIES_PATH, 'clRGinfo'), '-s'): 'clrginfo_s.txt',
    (os.path.join(UTILITIES_PATH, 'clRGinfo'), '-m'): 'clrginfo_m.txt',
    (CLRAS_PATH, 'sancomm_status'): 'clras_sancomm_status.txt',
    (CLRAS_PATH, 'dpcomm_status'): 'clras_dpcomm_status.txt',
    ('netstat', '-i'): 'netstat_i.txt',
    ('lsvg', '-o'): 'lsvg_o.txt',
    ('lsvg', '-p', 'datavg'): 'lsvg_p_datavg.txt',
    ('lsvg', '-p', 'appvg'): 'lsvg_p_appvg.txt',
}


def make_dispatch_side_effect(dispatch):
    def _side_effect(command, log, raise_on_empty_output=True, log_debug=True, env=None):
        key = tuple(command)
        if key not in dispatch:
            raise OSError('[Errno 2] No such file or directory: {!r}'.format(command[0]))
        return read_fixture(dispatch[key]), '', 0

    return _side_effect


@pytest.fixture
def happy_path_mock():
    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = make_dispatch_side_effect(HAPPY_PATH_DISPATCH)
        yield mock_get_subprocess_output


# ---------------------------------------------------------------------------
# Pure parser tests
# ---------------------------------------------------------------------------


def test_parse_odm_stanzas_cluster():
    stanzas = parsers.parse_odm_stanzas(read_fixture('odmget_hacmpcluster.txt'))
    assert len(stanzas) == 1
    assert stanzas[0]['name'] == 'prodcluster'
    assert stanzas[0]['heartbeattype'] == 'U'


def test_parse_odm_stanzas_cluster_multicast():
    stanzas = parsers.parse_odm_stanzas(read_fixture('odmget_hacmpcluster_multicast.txt'))
    assert stanzas[0]['heartbeattype'] == 'C'


def test_parse_odm_stanzas_node():
    stanzas = parsers.parse_odm_stanzas(read_fixture('odmget_hacmpnode.txt'))
    assert [s['name'] for s in stanzas] == ['node1', 'node2']


def test_parse_odm_stanzas_empty():
    assert parsers.parse_odm_stanzas('') == []


def test_parse_lssrc_state_stable():
    assert parsers.parse_lssrc_state(read_fixture('lssrc_clstrmgres_stable.txt')) == 'ST_STABLE'


def test_parse_lssrc_state_unstable():
    assert parsers.parse_lssrc_state(read_fixture('lssrc_clstrmgres_unstable.txt')) == 'ST_RP_RUNNING'


def test_parse_lssrc_state_broken():
    assert parsers.parse_lssrc_state(read_fixture('lssrc_clstrmgres_broken.txt')) == 'ST_BROKEN'


def test_parse_lssrc_state_missing():
    assert parsers.parse_lssrc_state('garbage output with no state line') is None


def test_parse_lslpp_version():
    version = parsers.parse_lslpp_version(read_fixture('lslpp_lc_cluster_es_server_rte.txt'))
    assert version == '7.2.7.1'


def test_find_last_event():
    event = parsers.find_last_event(read_fixture('hacmp_out_tail.txt'))
    assert event == 'node_up'


def test_find_last_event_none():
    assert parsers.find_last_event('nothing relevant here') is None


def test_parse_clrginfo_s():
    rows = parsers.parse_clrginfo_s(read_fixture('clrginfo_s.txt'))
    assert rows == [
        {'group': 'appRG', 'state': 'ONLINE', 'node': 'node1', 'site': None},
        {'group': 'appRG', 'state': 'OFFLINE', 'node': 'node2', 'site': None},
        {'group': 'dbRG', 'state': 'OFFLINE', 'node': 'node1', 'site': None},
        {'group': 'dbRG', 'state': 'ONLINE', 'node': 'node2', 'site': None},
    ]


def test_parse_clrginfo_s_rg_error():
    rows = parsers.parse_clrginfo_s(read_fixture('clrginfo_s_rg_error.txt'))
    assert rows[0] == {'group': 'appRG', 'state': 'ERROR', 'node': 'node1', 'site': None}


def test_parse_clrginfo_s_with_site():
    rows = parsers.parse_clrginfo_s(read_fixture('clrginfo_s_with_site.txt'))
    assert rows[0] == {'group': 'appRG', 'state': 'ONLINE', 'node': 'node1', 'site': 'siteA'}
    assert rows[1] == {'group': 'dbRG', 'state': 'ONLINE', 'node': 'node2', 'site': 'siteA'}


def test_parse_clrginfo_m():
    rows = parsers.parse_clrginfo_m(read_fixture('clrginfo_m.txt'))
    assert rows == [
        {'group': 'appRG', 'application': 'appMonitor1', 'node': 'node1', 'state': 'ONLINE'},
        {'group': 'appRG', 'application': 'appMonitor1', 'node': 'node2', 'state': 'OFFLINE'},
        {'group': 'dbRG', 'application': 'dbMonitor1', 'node': 'node2', 'state': 'ONLINE'},
        {'group': 'dbRG', 'application': 'dbMonitor1', 'node': 'node1', 'state': 'FAILED'},
    ]


def test_parse_lscluster_m_unicast():
    nodes = parsers.parse_lscluster_m(read_fixture('lscluster_m_unicast.txt'))
    assert len(nodes) == 2
    assert nodes[0] == {
        'node': 'node1',
        'state': 'UP',
        'points_of_contact': 1,
        'interfaces': [{'name': 'tcpsock->02', 'state': 'UP'}],
    }
    assert nodes[1] == {
        'node': 'node2',
        'state': 'UP',
        'points_of_contact': 1,
        'interfaces': [{'name': 'tcpsock->03', 'state': 'UP'}],
    }


BASE_METRICS = [
    'powerha.cluster.nodes',
    'powerha.cluster.nodes_up',
    'powerha.cluster_manager.stable',
    'powerha.cluster_manager.state',
    'powerha.node.state',
    'powerha.node.up',
    'powerha.resource_group.count',
    'powerha.resource_group.state',
    'powerha.resource_group.online',
    'powerha.caa.heartbeat_type',
    'powerha.caa.points_of_contact',
    'powerha.caa.interface.state',
    'powerha.caa.interface.up',
    'powerha.caa.san_comms.up',
    'powerha.caa.disk_comms.up',
    'powerha.network.interface.state',
    'powerha.network.interface.up',
    'powerha.volume_group.count',
    'powerha.volume_group.online',
    'powerha.volume_group.physical_volume.up',
    'powerha.volume_group.physical_volume.state',
    'powerha.volume_group.physical_volume.total_pps',
    'powerha.volume_group.physical_volume.free_pps',
]

APP_MONITOR_AND_COUNTER_METRICS = [
    'powerha.application_monitor.count',
    'powerha.application_monitor.state',
    'powerha.network.interface.errors_in.count',
    'powerha.network.interface.packets_out.count',
    'powerha.network.interface.errors_out.count',
    'powerha.network.interface.collisions.count',
]


def test_parse_lscluster_m_multicast_interfaces():
    nodes = parsers.parse_lscluster_m(read_fixture('lscluster_m_multicast.txt'))
    assert nodes[0]['interfaces'] == [{'name': 'en0', 'state': 'UP'}, {'name': 'en1', 'state': 'UP'}]


def test_parse_lscluster_m_node_down():
    nodes = parsers.parse_lscluster_m(read_fixture('lscluster_m_node_down.txt'))
    down = [n for n in nodes if n['node'] == 'node2'][0]
    assert down['state'] == 'DOWN'
    assert down['points_of_contact'] == 0


def test_parse_clras_status_sancomm():
    rows = parsers.parse_clras_status(read_fixture('clras_sancomm_status.txt'))
    assert rows[0]['node_name'] == 'node1'
    assert rows[0]['status'] == 'UP'
    assert rows[1]['node_name'] == 'node2'
    assert rows[1]['status'] == 'DOWN'


def test_parse_clras_status_dpcomm():
    rows = parsers.parse_clras_status(read_fixture('clras_dpcomm_status.txt'))
    assert all(row['status'] == 'UP' for row in rows)


def test_parse_netstat_i():
    interfaces = parsers.parse_netstat_i(read_fixture('netstat_i.txt'))
    names = [i['name'] for i in interfaces]
    assert names == ['en0', 'en1']
    en0 = interfaces[0]
    assert en0['up'] is True
    assert en0['ip_address'] == 'node1'
    assert en0['ipkts'] == 1520349
    assert en0['ierrs'] == 0
    assert en0['opkts'] == 1233221
    assert en0['oerrs'] == 0


def test_parse_netstat_i_iface_down():
    interfaces = parsers.parse_netstat_i(read_fixture('netstat_i_iface_down.txt'))
    by_name = {i['name']: i for i in interfaces}
    assert by_name['en0']['up'] is True
    assert by_name['en1']['up'] is False


def test_parse_lsvg_o():
    assert parsers.parse_lsvg_o(read_fixture('lsvg_o.txt')) == ['datavg', 'appvg', 'rootvg', 'caavg_private']


def test_parse_lsvg_p():
    rows = parsers.parse_lsvg_p(read_fixture('lsvg_p_datavg.txt'))
    assert rows == [
        {'name': 'hdisk2', 'state': 'active', 'total_pps': 511, 'free_pps': 200},
        {'name': 'hdisk3', 'state': 'active', 'total_pps': 511, 'free_pps': 200},
    ]


def test_parse_lsvg_p_missing_pv():
    rows = parsers.parse_lsvg_p(read_fixture('lsvg_p_datavg_missing_pv.txt'))
    assert rows[1] == {'name': 'hdisk3', 'state': 'missing', 'total_pps': 511, 'free_pps': 511}


# ---------------------------------------------------------------------------
# Full check tests (mocked subprocess dispatch)
# ---------------------------------------------------------------------------


def test_check_happy_path(dd_run_check, aggregator, happy_path_mock):
    check = PowerhaCheck('powerha', {}, [{}])
    dd_run_check(check)

    tags = ['powerha_cluster:prodcluster']

    aggregator.assert_service_check('powerha.can_connect', AgentCheck.OK, tags=tags)
    aggregator.assert_metric('powerha.cluster_manager.stable', 1, tags=tags)
    aggregator.assert_service_check('powerha.cluster_manager.status', AgentCheck.OK, tags=tags)

    node_tags = tags + ['peer_node:node1']
    aggregator.assert_metric('powerha.node.up', 1, tags=node_tags)
    aggregator.assert_service_check('powerha.node.status', AgentCheck.OK, tags=node_tags)

    rg_tags = tags + ['resource_group:appRG']
    aggregator.assert_service_check('powerha.resource_group.status', AgentCheck.OK, tags=rg_tags)
    aggregator.assert_metric(
        'powerha.resource_group.online', 1, tags=rg_tags + ['rg_node:node1']
    )
    aggregator.assert_metric(
        'powerha.resource_group.online', 0, tags=rg_tags + ['rg_node:node2']
    )

    caa_iface_tags = tags + ['peer_node:node1', 'interface:tcpsock->02']
    aggregator.assert_metric('powerha.caa.interface.up', 1, tags=caa_iface_tags)

    san_comms_up_tags = tags + ['peer_node:node1']
    san_comms_down_tags = tags + ['peer_node:node2']
    aggregator.assert_metric('powerha.caa.san_comms.up', 1, tags=san_comms_up_tags)
    aggregator.assert_metric('powerha.caa.san_comms.up', 0, tags=san_comms_down_tags)
    aggregator.assert_service_check('powerha.caa.san_comms.status', AgentCheck.WARNING, tags=san_comms_down_tags)

    net_iface_tags = tags + ['interface:en0']
    aggregator.assert_metric('powerha.network.interface.up', 1, tags=net_iface_tags)
    aggregator.assert_service_check('powerha.network.interface.status', AgentCheck.OK, tags=net_iface_tags)

    vg_tags = tags + ['volume_group:datavg']
    aggregator.assert_metric('powerha.volume_group.online', 1, tags=vg_tags)
    aggregator.assert_service_check('powerha.volume_group.status', AgentCheck.OK, tags=vg_tags)
    aggregator.assert_metric(
        'powerha.volume_group.physical_volume.total_pps', 511, tags=vg_tags + ['physical_volume:hdisk2']
    )

    for metric_name in BASE_METRICS:
        aggregator.assert_metric(metric_name)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_app_monitors_and_counters_enabled(dd_run_check, aggregator, happy_path_mock):
    instance = {
        'collect_app_monitor_status': True,
        'collect_network_interface_counters': True,
    }
    check = PowerhaCheck('powerha', {}, [instance])
    dd_run_check(check)

    tags = ['powerha_cluster:prodcluster']

    failed_tags = tags + ['resource_group:dbRG', 'application:dbMonitor1', 'monitor_node:node1']
    aggregator.assert_metric('powerha.application_monitor.online', 0, tags=failed_tags)
    aggregator.assert_service_check('powerha.application_monitor.status', AgentCheck.CRITICAL, tags=failed_tags)

    online_tags = tags + ['resource_group:appRG', 'application:appMonitor1', 'monitor_node:node1']
    aggregator.assert_metric('powerha.application_monitor.online', 1, tags=online_tags)

    net_iface_tags = tags + ['interface:en0']
    aggregator.assert_metric('powerha.network.interface.packets_in.count', 1520349, tags=net_iface_tags)

    for metric_name in BASE_METRICS + APP_MONITOR_AND_COUNTER_METRICS:
        aggregator.assert_metric(metric_name)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_multicast_heartbeat_and_rg_error(dd_run_check, aggregator):
    dispatch = dict(HAPPY_PATH_DISPATCH)
    dispatch[('odmget', 'HACMPcluster')] = 'odmget_hacmpcluster_multicast.txt'
    dispatch[(os.path.join(UTILITIES_PATH, 'clRGinfo'), '-s')] = 'clrginfo_s_rg_error.txt'
    dispatch[('lscluster', '-m')] = 'lscluster_m_multicast.txt'

    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = make_dispatch_side_effect(dispatch)
        check = PowerhaCheck('powerha', {}, [{}])
        dd_run_check(check)

    tags = ['powerha_cluster:prodcluster']
    aggregator.assert_metric('powerha.caa.heartbeat_type', 1, tags=tags + ['heartbeat_type:multicast'])
    aggregator.assert_service_check(
        'powerha.resource_group.status', AgentCheck.CRITICAL, tags=tags + ['resource_group:appRG']
    )


def test_check_missing_binary_is_critical(dd_run_check, aggregator):
    def _side_effect(command, log, raise_on_empty_output=True, log_debug=True, env=None):
        if command[0] == 'lssrc':
            raise OSError("[Errno 2] No such file or directory: 'lssrc'")
        raise OSError('[Errno 2] No such file or directory: {!r}'.format(command[0]))

    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = _side_effect
        check = PowerhaCheck('powerha', {}, [{}])
        dd_run_check(check)

    aggregator.assert_service_check(
        'powerha.can_connect', AgentCheck.CRITICAL, tags=['powerha_cluster:unknown']
    )


def test_check_garbage_lssrc_output_is_critical(dd_run_check, aggregator):
    dispatch = {('lssrc', '-ls', 'clstrmgrES'): None}

    def _side_effect(command, log, raise_on_empty_output=True, log_debug=True, env=None):
        if tuple(command) == ('lssrc', '-ls', 'clstrmgrES'):
            return 'not a recognizable status line\n', '', 0
        raise OSError('[Errno 2] No such file or directory: {!r}'.format(command[0]))

    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = _side_effect
        check = PowerhaCheck('powerha', {}, [{}])
        dd_run_check(check)

    aggregator.assert_service_check(
        'powerha.can_connect', AgentCheck.CRITICAL, tags=['powerha_cluster:unknown']
    )


def test_check_unstable_cluster_manager_looks_up_event(dd_run_check, aggregator, tmpdir):
    hacmp_out = tmpdir.join('hacmp.out')
    hacmp_out.write(read_fixture('hacmp_out_tail.txt'))

    dispatch = dict(HAPPY_PATH_DISPATCH)
    dispatch[('lssrc', '-ls', 'clstrmgrES')] = 'lssrc_clstrmgres_unstable.txt'

    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = make_dispatch_side_effect(dispatch)
        check = PowerhaCheck('powerha', {}, [{'hacmp_out_path': str(hacmp_out)}])
        dd_run_check(check)

    tags = ['powerha_cluster:prodcluster']
    aggregator.assert_metric('powerha.cluster_manager.stable', 0, tags=tags)
    service_checks = aggregator.service_checks('powerha.cluster_manager.status')
    assert len(service_checks) == 1
    assert service_checks[0].status == AgentCheck.WARNING
    assert 'node_up' in service_checks[0].message


def test_check_hacmp_out_permission_denied_is_handled(dd_run_check, aggregator):
    dispatch = dict(HAPPY_PATH_DISPATCH)
    dispatch[('lssrc', '-ls', 'clstrmgrES')] = 'lssrc_clstrmgres_unstable.txt'

    with mock.patch('datadog_checks.powerha.check.get_subprocess_output') as mock_get_subprocess_output:
        mock_get_subprocess_output.side_effect = make_dispatch_side_effect(dispatch)
        check = PowerhaCheck('powerha', {}, [{'hacmp_out_path': '/nonexistent/hacmp.out'}])
        dd_run_check(check)

    service_checks = aggregator.service_checks('powerha.cluster_manager.status')
    assert len(service_checks) == 1
    assert service_checks[0].status == AgentCheck.WARNING
    assert 'event' not in service_checks[0].message
