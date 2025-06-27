# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
import subprocess
import yaml
from dataclasses import dataclass
import re

OSS_JOBSTATS_PARAM_REGEX = r'ost.*.job_stats'
MDS_JOBSTATS_PARAM_REGEX = r'obdfilter.*.job_stats'

IGNORED_STATS = {
    'snapshot_time',
    'start_time',
    'elapsed_time',
}

@dataclass
class LustreParam:
    regex: str
    node_types: tuple[str, ...]
    wildcards: tuple[str, ...] = ()
    prefix: str = ''

DEFAULT_PARAMS = [
    LustreParam(regex='llite.*.stats', node_types=('client',), wildcards=('device_uuid',), prefix='filesystem'),
]

EXTRA_PARAMS = [
    LustreParam(regex='mds.MDS.mdt.stats', node_types=('mds',), prefix='mds.mdt'),
    LustreParam(regex='mdt.*.exports.*.stats', node_types=('mds',), wildcards=('device_name','nid'), prefix='mds.mdt.exports'),
    LustreParam(regex='mdc.*.stats', node_types=('client',), wildcards=('device_uuid',), prefix='mdc'),
    LustreParam(regex='ldlm.services.*.stats', node_types=('client', 'mds', 'oss'), wildcards=('ldlm_service',), prefix='ldlm.services'),
    LustreParam(regex='ldlm.namespaces.*.pool.stats', node_types=('client', 'mds', 'oss'), wildcards=('device_uuid',), prefix='ldlm.namespaces.pool'),
    LustreParam(regex='mgs.MGS.exports.*.stats', node_types=('mds',), wildcards=('device_name', 'nid'), prefix='mgs.exports'),
    LustreParam(regex='ost.OSS.oss.stats', node_types=('oss',), prefix='ost.oss'),
    LustreParam(regex='osc.*.stats', node_types=('client',), wildcards=('device_uuid',), prefix='osc'),
    LustreParam(regex='obdfilter.*.exports.*.stats', node_types=('oss',), wildcards=('device_name', 'nid'), prefix='obdfilter.exports'),
    LustreParam(regex='obdfilter.*.stats', node_types=('oss',), wildcards=('device_name',), prefix='obdfilter'),
]

class LustreCheck(AgentCheck):

    __NAMESPACE__ = 'lustre'

    def __init__(self, name, init_config, instances):
        super(LustreCheck, self).__init__(name, init_config, instances)

        # Paths to Lustre binaries
        self.lctl_path = self.instance.get("lctl_path", "/usr/sbin/lctl")
        self.lnetctl_path = self.instance.get("lnetctl_path", "/usr/sbin/lnetctl")
        self.lfs_path = self.instance.get("lfs_path", "/usr/bin/lfs")
        # Enable or disable specific metrics
        self.lnetctl_detailed = self.instance.get("enable_lnetctl_detailed", False)
        self.lnetctl_health = self.instance.get("enable_lnetctl_health", False)

        self.changelog_lines_per_run = self.instance.get("changelog_lines_per_check", 1000)

        self.devices = []
        self.changelog_targets = []
        self.filesystems = self.instance.get("filesystems", [])
        self.node_type = self.instance.get("node_type", self._find_node_type())

        self.param_list = DEFAULT_PARAMS
        if self.instance.get("enable_extra_params", False):
            self.param_list += EXTRA_PARAMS




    def check(self, _):
        self.submit_jobstats_metrics()
        # self.submit_lnet_metrics()
        # self.submit_lnet_local_ni_metrics()
        # self.submit_lnet_peer_ni_metrics()

    def _find_node_type(self):
        '''
        Determine the host type from the command line.
        '''
        self.log.debug('Determining node type...')
        try:
            if not self.devices:
                self._update_devices()
            device_types = [device['type'] for device in self.devices]
            
            if 'mdt' in device_types:
                return 'mds'
            elif 'ost' in device_types:
                return 'oss'
            else:
                return 'client'
        except Exception as e:
            self.log.error(f'Failed to determine node type: {e}')
            return 'client'

    def update(self):
        '''
        Update the check by finding devices and filesystems.
        '''
        self.log.debug('Updating Lustre check...')
        self._update_devices()
        self._update_filesystems()
        self._update_changelog_targets()

    def _update_devices(self):
        '''
        Find devices using the lctl dl command.
        '''
        output = self.run_command(self.lctl_path, 'dl', '-y')
        device_data = yaml.safe_load(output)
        self.devices = device_data.get('devices', [])

    def _update_filesystems(self):
        '''
        Find filesystems using the lctl list_param command.
        '''
        self.log.debug('Finding filesystems...')
        if self.node_type.lower() == 'mds':
            param_regex = MDS_JOBSTATS_PARAM_REGEX
            filesystem_regex = r'(?<=obdfilter\.).*(?=-OST)'
        elif self.node_type.lower() == 'oss':
            param_regex = OSS_JOBSTATS_PARAM_REGEX
            filesystem_regex = r'(?<=mds\.).*(?=-MDT)'
        elif self.node_type.lower() == 'client':
            param_regex = 'llite.*.stats'
            filesystem_regex = r'(?<=llite\.).*(?=-[^-]*\.stats)'
        else:
            self.log.debug(f'Invalid node_type: {self.node_type}')
            return
        try:
            raw_output = self.run_command(self.lctl_path, "list_param", param_regex, sudo=True)
            lines = raw_output.splitlines()
            filesystems = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                match = re.search(filesystem_regex, line)
                if match:
                    filesystem = match.group(0)
                    filesystems.append(filesystem)
            self.filesystems = list(set(filesystems))  # Remove duplicates
        except Exception as e:
            self.log.error(f'Failed to find filesystems: {e}')
            return

    def _update_changelog_targets(self):
        target_regex = [filesystem+r'-MDT\d\d\d\d' for filesystem in self.filesystems]
        targets = []
        for device in self.devices:
            for regex in target_regex:
                match = re.search(regex, device['name'])
                if match:
                    targets.append(match.group(0))
        self.changelog_targets = list(set(targets)) # Remove duplicates

    def run_command(self, bin, *args, sudo=False):
        '''
        Run a command using the given binary.
        '''
        cmd = f' {"sudo " if sudo else ""}{bin}{" ".join(args)}'
        try:
            return subprocess.run(cmd, timeout=5, shell=True, capture_output=True, text=True).stdout
        except Exception as e:
            self.log.error(f'Failed to run command {cmd}: {e}')
            return ''

    def submit_jobstats_metrics(self):
        '''
        Submit the jobstats metrics to Datadog.
        '''
        jobstats_params = self.get_jobstats_params_list()
        for jobstats_param in jobstats_params:
            device_name = jobstats_param.split('.')[1]  # For example: lustre-MDT0000
            if self.filesystems and not any(device_name.startswith(filesystem) for filesystem in self.filesystems):
                continue
            jobstats_metrics = self.get_jobstats_metrics(jobstats_param)['job_stats']
            for job in jobstats_metrics:
                job_id = job['job_id']
                for metric_name, metric_values in job.items():
                    if not isinstance(metric_values, dict):
                        continue
                    for metric_type, metric_value in metric_values.items():
                        if metric_type == 'unit':
                            continue
                        if metric_type == 'hist':
                            # TODO: Handle histogram metrics if needed
                            continue 
                        self.log.warning(f'Jobstats metric {metric_name} with type {metric_type} has value {metric_value}')
                        self.gauge(f'job_stats.{metric_name}.{metric_type}', metric_value, tags=[f'device_type:{self.node_type}', f'device_name:{device_name}', f'job_id:{job_id}'])


    def get_jobstats_params_list(self):
        '''
        Get the jobstats params from the command line.
        '''
        if self.node_type.lower() == 'mds':
            param_regex = MDS_JOBSTATS_PARAM_REGEX
        elif self.node_type.lower() == 'oss':
            param_regex = OSS_JOBSTATS_PARAM_REGEX
        elif self.node_type.lower() == 'client':
            self.log.debug(f'Client device_type has no jobstats parameters.')
            return []
        else:
            self.log.debug(f'Invalid device_type: {self.node_type}')
            return []
        raw_params = self.run_command(self.lctl_path, "list_param", param_regex, sudo=True)
        return [line.strip() for line in raw_params.splitlines() if line.strip()]


    def get_jobstats_metrics(self, jobstats_param):
        '''
        Get the jobstats metrics for a given jobstats param.
        '''
        jobstats_output = self.run_command(self.lctl_path, "get_param", "-ny", jobstats_param, sudo=True)
        try:
            return yaml.safe_load(jobstats_output)
        except KeyError:
            self.log.debug(f'No jobstats metrics found for {jobstats_param}')
            return {}
    
    def submit_lnet_stats_metrics(self):
        '''
        Submit the lnet metrics.
        '''
        lnet_metrics = self.get_lnet_metrics('stats')['statistics']
        for metric in lnet_metrics:
            self.gauge(f'net.{metric}', lnet_metrics[metric], tags=[f'node_type:{self.node_type}'])

    def get_lnet_metrics(self, stats_type='stats'):
        '''
        Get the lnet stats from the command line.
        '''
        lnet_stats = self.run_command(self.lnetctl_path, stats_type, 'show', '-v', '3', sudo=True)
        try:
            return yaml.safe_load(lnet_stats)
        except (KeyError, ValueError):
            self.log.debug(f'No lnet stats found')
            return {}
    
    def submit_lnet_local_ni_metrics(self):
        '''
        Submit the lnet local ni metrics.
        '''
        lnet_local_stats = self.get_lnet_metrics('net')['net']
        for net in lnet_local_stats:
            net_type = net.get('net type')
            for ni in net.get('local NI(s)', []):
                nid = ni.get('nid')
                tags = [f'net_type:{net_type}', f'nid:{nid}']
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    for metric_name, metric_value in stats_group.items():
                        if isinstance(metric_value, int):
                            self.gauge(f'net.local.{stats_group_name.replace(" ", "_")}.{metric_name.replace(" ", "_")}', metric_value, tags=tags)

    def submit_lnet_peer_ni_metrics(self):
        '''
        Submit the lnet peer ni metrics.
        '''
        lnet_peer_stats = self.get_lnet_metrics('peer')['peer']
        for peer in lnet_peer_stats:
            nid = peer.get('primary nid')
            for ni in peer.get('peer ni', []):
                peer_nid = ni.get('nid')
                tags = [f'nid:{nid}', f'peer_nid:{peer_nid}']
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    for metric_name, metric_value in stats_group.items():
                        if isinstance(metric_value, int):
                            self.gauge(f'net.peer.{stats_group_name.replace(" ", "_")}.{metric_name.replace(" ", "_")}', metric_value, tags=tags)

    def submit_general_stats(self):
        '''
        Submit general stats.
        '''
        for param in self.param_list: 
            if not param.regex.endswith('.stats'):
                continue
            raw_stats = self.run_command(self.lctl_path, "get_param", "-ny", param.regex, sudo=True)
            parsed_stats = self.parse_stats(raw_stats)
            for stat_name, stat_value in parsed_stats.items():
                if isinstance(stat_value, int):
                    self.gauge(f'general.{stat_name}', stat_value, tags=[f'node_type:{self.node_type}'])
                    continue
                if not isinstance(stat_value, dict):
                    self.log.debug(f'Unexpected stat value for {stat_name}: {stat_value}')
                    continue
                for metric_type, metric_value in stat_value.items():
                    if isinstance(metric_value, int):
                        self.gauge(f'general.{stat_name}.{metric_type}', metric_value, tags=[f'node_type:{self.node_type}'])
                    else:
                        self.log.debug(f'Unexpected metric value for {stat_name}.{metric_type}: {metric_value}')

    def parse_stats(self, raw_stats):
        '''
        Parse the raw stats into a dictionary.
        '''
        stats = {}
        for line in raw_stats.splitlines():
            # elapsed_time              2068792.478877751 secs.nsecs
            # req_waittime              83 samples [usecs] 11 40 1493 32135
            # req_qdepth                83 samples [reqs] 0 0 0 0
            # cancel                    253 samples [locks] 1 1 253
            # tgtreg                    2 samples [reqs]
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            stat_name = parts[0]
            if stat_name in IGNORED_STATS:
                continue
            try:
                stat_value = {"count": int(parts[1]), "unit": parts[3].strip('[]')}
                stat_types = ('min', 'max', 'sum', 'sumsq')
                for i, value in enumerate(parts[4:]):
                    stat_value[stat_types[i]] = int(value)
                if len(parts) > 8:
                    self.log.debug(f'Unexpected format for stat "{line}"')
            except ValueError:
                self.log.debug(f'Could not parse stat value for "{line}"')
                continue
            stats[stat_name] = stat_value
        return stats

    def submit_device_health(self):
        '''
        Submit device health metrics based on device status from lctl dl command.
        '''
        try:
            self._update_devices()
            
            for device in self.devices:
                device_status = 1 if device['status'] == 'UP' else 0
                tags = [
                    f'device_type:{device.get("type", "unknown")}',
                    f'device_name:{device.get("name", "unknown")}',
                    f'device_uuid:{device.get("uuid", "unknown")}',
                    f'node_type:{self.node_type}'
                ]
                
                self.gauge('device.health', device_status, tags=tags)
                self.gauge('device.refcount', device['refcount'], tags=tags)
                
        except Exception as e:
            self.log.error(f'Failed to submit device health metrics: {e}')
    
    # Only on client nodes
    def submit_changelogs(self):
        '''
        Get changelogs from the command line.
        '''
        for target in self.changelog_targets:
            changelog = self.get_changelog(target)
            changelog_lines = changelog.splitlines()
            for line in changelog_lines:
                if not line.strip():
                    continue
                parts = line.split()
                try:
                    data = {
                        'operation_type': parts[1],
                        'timestamp': parts[2],
                        'datestamp': parts[3],
                        'flags': parts[4],
                        'message': ' '.join(parts[5:])
                    }
                except IndexError:
                    self.log.debug(f'Unexpected changelog format: {line}')
                    continue
                self.send_log(data, {'index': parts[0]}, stream=target)


    def get_changelog(self, target):
        self.log.info(f'Collecting changelogs for: {target}')
        index_from_memory = self.get_log_cursor(stream=target) 
        start_index = '0' if index_from_memory is None else index_from_memory
        end_index = str(int(start_index) + int(self.changelog_lines_per_run))
        return self.run_command(self.lfs_path, 'changelog', target, start_index, end_index, sudo=True)
