# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, List, Optional  # noqa: F401

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

from .parsers import (
    find_last_event,
    parse_clras_status,
    parse_clrginfo_m,
    parse_clrginfo_s,
    parse_lscluster_m,
    parse_lslpp_version,
    parse_lssrc_state,
    parse_lsvg_o,
    parse_lsvg_p,
    parse_netstat_i,
    parse_odm_stanzas,
)

CLUSTER_MANAGER_OK_STATES = frozenset({'ST_STABLE'})
CLUSTER_MANAGER_WARNING_STATES = frozenset(
    {
        'ST_INIT',
        'ST_JOINING',
        'ST_VOTING',
        'ST_RP_RUNNING',
        'ST_BARRIER',
        'ST_CBARRIER',
        'ST_UNSTABLE',
        'NOT_CONFIGURED',
    }
)

RG_OK_STATES = frozenset({'ONLINE', 'ONLINE_SECONDARY'})
RG_WARNING_STATES = frozenset({'ACQUIRING', 'RELEASING', 'UNMANAGED'})
RG_CRITICAL_STATES = frozenset({'ERROR', 'ERROR_SECONDARY'})


class PowerhaCheck(AgentCheck):
    """
    Collects IBM PowerHA SystemMirror / HACMP cluster health as structured
    metrics and service checks. This check must run locally on an AIX
    PowerHA cluster node; it shells out to the same PowerHA/AIX utilities
    used by the classic `qha` status script, but performs no remote
    `clrsh` fan-out -- peer node visibility comes from `lscluster -m`,
    which reports the CAA view of every cluster member from any node.
    """

    __NAMESPACE__ = 'powerha'

    def __init__(self, name, init_config, instances):
        super(PowerhaCheck, self).__init__(name, init_config, instances)

        self._utilities_path = self.instance.get('utilities_path', '/usr/es/sbin/cluster/utilities')
        self._clras_path = self.instance.get('clras_path', '/usr/lib/cluster/clras')
        self._hacmp_out_path_override = self.instance.get('hacmp_out_path')
        self._cluster_name_override = self.instance.get('cluster_name')

        self._collect_resource_groups = is_affirmative(self.instance.get('collect_resource_groups', True))
        self._collect_app_monitor_status = is_affirmative(self.instance.get('collect_app_monitor_status', False))
        self._collect_caa_comms = is_affirmative(self.instance.get('collect_caa_comms', True))
        self._collect_network_interfaces = is_affirmative(self.instance.get('collect_network_interfaces', True))
        self._collect_network_interface_counters = is_affirmative(
            self.instance.get('collect_network_interface_counters', False)
        )
        self._submit_ip_address_tag = is_affirmative(self.instance.get('submit_ip_address_tag', False))
        self._collect_volume_groups = is_affirmative(self.instance.get('collect_volume_groups', True))
        self._collect_cluster_events = is_affirmative(self.instance.get('collect_cluster_events', True))
        self._exclude_volume_groups = set(
            self.instance.get('exclude_volume_groups', ['rootvg', 'caavg_private'])
        )

        self._warned_missing_binaries = set()

    def check(self, _):
        # type: (Any) -> None
        base_tags = list(self.instance.get('tags', []))

        cluster_name = self._cluster_name_override
        heartbeat_type = None
        node_names = []

        cluster_info = self._run_domain('cluster identity', self._discover_cluster)
        if cluster_info is not None:
            cluster_name, heartbeat_type, node_names = cluster_info

        tags = base_tags + ['powerha_cluster:{}'.format(cluster_name or 'unknown')]

        self._run_domain('version metadata', self._collect_version_metadata)

        cluster_manager_state = self._run_domain('cluster manager', self._collect_cluster_manager, tags)

        self._run_domain('cluster topology', self._collect_cluster_topology, tags, node_names)

        if self._collect_resource_groups:
            self._run_domain('resource groups', self._collect_resource_group_rows, tags)
        if self._collect_app_monitor_status:
            self._run_domain('application monitors', self._collect_app_monitors, tags)
        if self._collect_caa_comms:
            self._run_domain('CAA communications', self._collect_caa, tags, heartbeat_type)
        if self._collect_network_interfaces:
            self._run_domain('network interfaces', self._collect_network_interfaces_domain, tags)
        if self._collect_volume_groups:
            self._run_domain('volume groups', self._collect_volume_groups_domain, tags)

        if cluster_manager_state is None:
            self.service_check(
                'can_connect', AgentCheck.CRITICAL, tags=tags, message='Unable to query clstrmgrES state'
            )
        else:
            self.service_check('can_connect', AgentCheck.OK, tags=tags)

    def _run_domain(self, name, fn, *args):
        try:
            return fn(*args)
        except Exception as e:
            self.log.warning('Failed to collect %s: %s', name, e)
            return None

    def _run(self, argv, empty_ok=True):
        # type: (List[str], bool) -> Optional[str]
        binary = argv[0]
        try:
            out, err, returncode = get_subprocess_output(argv, self.log, raise_on_empty_output=not empty_ok)
        except OSError as e:
            self._warn_once(binary, 'binary not found or not executable: {}'.format(e))
            return None
        except Exception as e:
            self._warn_once(binary, 'failed to execute: {}'.format(e))
            return None

        if returncode != 0:
            self._warn_once(binary, 'exited with status {}: {}'.format(returncode, (err or '').strip()))
            return None

        if not out and not empty_ok:
            self._warn_once(binary, 'produced no output')
            return None

        return out

    def _warn_once(self, binary, message):
        key = (binary, message)
        if key in self._warned_missing_binaries:
            self.log.debug('%s %s', binary, message)
        else:
            self._warned_missing_binaries.add(key)
            self.log.warning('%s %s', binary, message)

    def _submit_state(
        self, metric_base, state, tags, sc_mapping, bool_metric, sc_name=None, default_status=AgentCheck.UNKNOWN, message=None
    ):
        """
        Shared emitter for the "gauge=1 with state: tag, 0/1 boolean gauge,
        service check" pattern used by every domain in this check.

        sc_mapping maps upper-cased state strings to AgentCheck statuses
        (OK/WARNING/CRITICAL); anything not in the mapping uses default_status.
        bool_metric is the full metric name (e.g. 'node.up') for the 0/1
        gauge; pass None to skip emitting it.
        """
        state_upper = (state or 'unknown').upper()
        state_tags = tags + ['state:{}'.format(state_upper.lower())]

        self.gauge('{}.state'.format(metric_base), 1, tags=state_tags)

        status = sc_mapping.get(state_upper, default_status)

        if bool_metric:
            is_up = 1 if status == AgentCheck.OK else 0
            self.gauge(bool_metric, is_up, tags=tags)

        if sc_name:
            self.service_check(sc_name, status, tags=tags, message=None if status == AgentCheck.OK else message)

    def _discover_cluster(self):
        out = self._run(['odmget', 'HACMPcluster'], empty_ok=False)
        if out is None:
            return None
        stanzas = parse_odm_stanzas(out)
        if not stanzas:
            return None
        cluster = stanzas[0]
        cluster_name = self._cluster_name_override or cluster.get('name')
        heartbeat_type = cluster.get('heartbeattype')

        node_out = self._run(['odmget', 'HACMPnode'])
        node_names = []
        if node_out:
            for stanza in parse_odm_stanzas(node_out):
                name = stanza.get('name')
                if name and name not in node_names:
                    node_names.append(name)

        return cluster_name, heartbeat_type, node_names

    def _collect_version_metadata(self):
        out = self._run(['lslpp', '-Lc', 'cluster.es.server.rte'])
        if not out:
            return
        version = parse_lslpp_version(out)
        if version:
            self.set_metadata('version', version)

    def _collect_cluster_manager(self, tags):
        out = self._run(['lssrc', '-ls', 'clstrmgrES'])
        if out is None:
            return None

        state = parse_lssrc_state(out)
        if state is None:
            return None

        sc_mapping = {}
        for s in CLUSTER_MANAGER_OK_STATES:
            sc_mapping[s] = AgentCheck.OK
        for s in CLUSTER_MANAGER_WARNING_STATES:
            sc_mapping[s] = AgentCheck.WARNING

        message = 'Current state: {}'.format(state)
        event = None
        if state not in CLUSTER_MANAGER_OK_STATES and self._collect_cluster_events:
            event = self._run_domain('cluster event lookup', self._find_running_event)
            if event:
                message = '{} (event: {})'.format(message, event)

        self.gauge('cluster_manager.stable', 1 if state in CLUSTER_MANAGER_OK_STATES else 0, tags=tags)
        self._submit_state(
            'cluster_manager',
            state,
            tags,
            sc_mapping,
            bool_metric=None,
            sc_name='cluster_manager.status',
            default_status=AgentCheck.CRITICAL,
            message=message,
        )

        return state

    def _find_running_event(self):
        path = self._hacmp_out_path_override
        if not path:
            logs_out = self._run(['odmget', '-q', 'name=hacmp.out', 'HACMPlogs'])
            if not logs_out:
                return None
            stanzas = parse_odm_stanzas(logs_out)
            if not stanzas or not stanzas[0].get('value'):
                return None
            path = stanzas[0]['value'].rstrip('/') + '/hacmp.out'

        try:
            with open(path, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 65536), 0)
                tail = f.read().decode('utf-8', errors='replace')
        except (OSError, PermissionError) as e:
            self.log.debug('Unable to read %s: %s', path, e)
            return None

        return find_last_event(tail)

    def _collect_cluster_topology(self, tags, node_names):
        self.gauge('cluster.nodes', len(node_names), tags=tags)

        caa_out = self._run(['lscluster', '-m'])
        if not caa_out:
            return

        caa_nodes = parse_lscluster_m(caa_out)
        nodes_up = sum(1 for n in caa_nodes if n['state'] == 'UP')
        self.gauge('cluster.nodes_up', nodes_up, tags=tags)

        for node in caa_nodes:
            node_tags = tags + ['peer_node:{}'.format(node['node'])]
            sc_mapping = {'UP': AgentCheck.OK, 'DOWN': AgentCheck.CRITICAL}
            self._submit_state(
                'node',
                node['state'],
                node_tags,
                sc_mapping,
                bool_metric='node.up',
                sc_name='node.status',
                default_status=AgentCheck.UNKNOWN,
            )

    def _collect_resource_group_rows(self, tags):
        out = self._run(self._utility(['clRGinfo', '-s']))
        if out is None:
            out = self._run(self._utility(['clfindres', '-s']))
        if not out:
            return []

        rows = parse_clrginfo_s(out)

        self.gauge('resource_group.count', len({row['group'] for row in rows}), tags=tags)

        by_group = {}
        for row in rows:
            row_tags = tags + ['resource_group:{}'.format(row['group']), 'rg_node:{}'.format(row['node'])]
            if row['site']:
                row_tags = row_tags + ['rg_site:{}'.format(row['site'])]

            state_upper = row['state'].upper()
            self.gauge('resource_group.state', 1, tags=row_tags + ['state:{}'.format(state_upper.lower())])
            self.gauge('resource_group.online', 1 if state_upper in RG_OK_STATES else 0, tags=row_tags)

            by_group.setdefault(row['group'], []).append(row)

        for group, group_rows in by_group.items():
            group_tags = tags + ['resource_group:{}'.format(group)]
            states = {r['state'].upper() for r in group_rows}

            if states & RG_CRITICAL_STATES or not (states & RG_OK_STATES):
                status = AgentCheck.CRITICAL
            elif states & RG_WARNING_STATES:
                status = AgentCheck.WARNING
            else:
                status = AgentCheck.OK

            message = None
            if status != AgentCheck.OK:
                online_nodes = [r['node'] for r in group_rows if r['state'].upper() in RG_OK_STATES]
                message = (
                    'Online on: {}'.format(', '.join(online_nodes)) if online_nodes else 'Not online on any node'
                )
            self.service_check('resource_group.status', status, tags=group_tags, message=message)

        return rows

    def _collect_app_monitors(self, tags):
        out = self._run(self._utility(['clRGinfo', '-m']))
        if not out:
            return

        rows = parse_clrginfo_m(out)
        self.gauge('application_monitor.count', len({(r['group'], r['application']) for r in rows}), tags=tags)

        sc_mapping = {'ONLINE': AgentCheck.OK, 'FAILED': AgentCheck.CRITICAL, 'OFFLINE': AgentCheck.WARNING}
        for row in rows:
            row_tags = tags + [
                'resource_group:{}'.format(row['group']),
                'application:{}'.format(row['application']),
                'monitor_node:{}'.format(row['node']),
            ]
            self._submit_state(
                'application_monitor',
                row['state'],
                row_tags,
                sc_mapping,
                bool_metric='application_monitor.online',
                sc_name='application_monitor.status',
                default_status=AgentCheck.UNKNOWN,
            )

    def _collect_caa(self, tags, heartbeat_type):
        heartbeat_label = {'C': 'multicast', 'U': 'unicast'}.get(heartbeat_type, 'unknown')
        self.gauge('caa.heartbeat_type', 1, tags=tags + ['heartbeat_type:{}'.format(heartbeat_label)])

        caa_out = self._run(['lscluster', '-m'])
        if caa_out:
            for node in parse_lscluster_m(caa_out):
                node_tags = tags + ['peer_node:{}'.format(node['node'])]
                self.gauge('caa.points_of_contact', node['points_of_contact'], tags=node_tags)

                for interface in node['interfaces']:
                    iface_tags = node_tags + ['interface:{}'.format(interface['name'])]
                    sc_mapping = {'UP': AgentCheck.OK, 'DOWN': AgentCheck.CRITICAL}
                    self._submit_state(
                        'caa.interface',
                        interface['state'],
                        iface_tags,
                        sc_mapping,
                        bool_metric='caa.interface.up',
                        sc_name='caa.interface.status',
                        default_status=AgentCheck.UNKNOWN,
                    )

        self._collect_clras_status('sancomm_status', 'caa.san_comms', tags)
        self._collect_clras_status('dpcomm_status', 'caa.disk_comms', tags)

    def _collect_clras_status(self, subcommand, metric_base, tags):
        out = self._run([self._clras_path, subcommand])
        if not out:
            return

        for row in parse_clras_status(out):
            node = row.get('node_name')
            status = (row.get('status') or '').upper()
            if not node:
                continue

            row_tags = tags + ['peer_node:{}'.format(node)]
            self.gauge('{}.up'.format(metric_base), 1 if status == 'UP' else 0, tags=row_tags)
            sc_mapping = {'UP': AgentCheck.OK, 'DOWN': AgentCheck.WARNING}
            self.service_check(
                '{}.status'.format(metric_base),
                sc_mapping.get(status, AgentCheck.WARNING),
                tags=row_tags,
            )

    def _collect_network_interfaces_domain(self, tags):
        out = self._run(['netstat', '-i'])
        if not out:
            return

        for iface in parse_netstat_i(out):
            iface_tags = tags + ['interface:{}'.format(iface['name'])]
            if self._submit_ip_address_tag and iface['ip_address']:
                iface_tags = iface_tags + ['ip_address:{}'.format(iface['ip_address'])]

            state = 'UP' if iface['up'] else 'DOWN'
            sc_mapping = {'UP': AgentCheck.OK, 'DOWN': AgentCheck.CRITICAL}
            self._submit_state(
                'network.interface',
                state,
                iface_tags,
                sc_mapping,
                bool_metric='network.interface.up',
                sc_name='network.interface.status',
                default_status=AgentCheck.UNKNOWN,
            )

            if self._collect_network_interface_counters:
                counter_names = ('ipkts', 'ierrs', 'opkts', 'oerrs', 'collisions')
                metric_names = (
                    'packets_in.count',
                    'errors_in.count',
                    'packets_out.count',
                    'errors_out.count',
                    'collisions.count',
                )
                for counter_name, metric_name in zip(counter_names, metric_names):
                    value = iface.get(counter_name)
                    if value is not None:
                        self.monotonic_count(
                            'network.interface.{}'.format(metric_name), value, tags=iface_tags
                        )

    def _collect_volume_groups_domain(self, tags):
        out = self._run(['lsvg', '-o'])
        if not out:
            return

        vgs = [vg for vg in parse_lsvg_o(out) if vg not in self._exclude_volume_groups]
        self.gauge('volume_group.count', len(vgs), tags=tags)

        for vg in vgs:
            vg_tags = tags + ['volume_group:{}'.format(vg)]
            self.gauge('volume_group.online', 1, tags=vg_tags)

            pv_out = self._run(['lsvg', '-p', vg])
            if not pv_out:
                continue

            pv_rows = parse_lsvg_p(pv_out)
            all_active = True
            for pv in pv_rows:
                pv_state = pv['state'].lower()
                is_active = pv_state == 'active'
                all_active = all_active and is_active

                pv_tags = vg_tags + ['physical_volume:{}'.format(pv['name'])]
                self.gauge('volume_group.physical_volume.up', 1 if is_active else 0, tags=pv_tags)
                self.gauge(
                    'volume_group.physical_volume.state',
                    1,
                    tags=pv_tags + ['state:{}'.format(pv_state)],
                )
                self.gauge('volume_group.physical_volume.total_pps', pv['total_pps'], tags=pv_tags)
                self.gauge('volume_group.physical_volume.free_pps', pv['free_pps'], tags=pv_tags)

            status = AgentCheck.OK if all_active else AgentCheck.CRITICAL
            self.service_check('volume_group.status', status, tags=vg_tags)

    def _utility(self, argv):
        argv = list(argv)
        argv[0] = os.path.join(self._utilities_path, argv[0])
        return argv
