# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck, is_affirmative  # noqa: F401
import subprocess
import yaml
from dataclasses import dataclass
import re
import time

OSS_JOBSTATS_PARAM_REGEX = r'obdfilter.*.job_stats'
MDS_JOBSTATS_PARAM_REGEX = r'mdt.*.job_stats'

IGNORED_STATS = {
    'snapshot_time',
    'start_time',
    'elapsed_time',
}

class LustreCheck(AgentCheck):

    __NAMESPACE__ = 'lustre'

    def __init__(self, name, init_config, instances):
        super(LustreCheck, self).__init__(name, init_config, instances)

        # Paths to Lustre binaries
        self.lctl_path = self.instance.get("lctl_path", "/usr/sbin/lctl")
        self.lnetctl_path = self.instance.get("lnetctl_path", "/usr/sbin/lnetctl")
        self.lfs_path = self.instance.get("lfs_path", "/usr/bin/lfs")
        # Enable or disable specific metrics
        self.enable_changelogs = is_affirmative(self.instance.get("enable_changelogs", False))
        self.lnetctl_verbosity = '3' if is_affirmative(self.instance.get("enable_lnetctl_detailed", False)) else '1'
        self.param_list = DEFAULT_PARAMS
        if self.instance.get("enable_extra_params", False):
            self.param_list += EXTRA_PARAMS

        self.changelog_lines_per_check = int(self.instance.get("changelog_lines_per_check", 1000))

        self.devices = []
        self.changelog_targets = []
        self.filesystems = self.instance.get("filesystems", [])
        self.node_type = self.instance.get("node_type", self._find_node_type())

        self.tags = self.instance.get('tags', [])
        self.tags.append(f'node_type:{self.node_type}')
        version = self.run_command(self.lctl_path, "get_param", "-ny", "version").strip()
        self.tags.append(f'lustre_version:{version}')

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

    def check(self, _):
        self.update()
        if self.node_type == 'client' and self.enable_changelogs:
            self.submit_changelogs()

        self.submit_device_health()
        self.submit_general_stats()
        self.submit_lnet_stats_metrics()
        self.submit_lnet_local_ni_metrics()
        self.submit_lnet_peer_ni_metrics()

        if self.node_type in ('mds', 'oss'):
            self.submit_jobstats_metrics()

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
            # obdfilter.<filesystem>-OST0000.job_stats
            filesystem_regex = r'(?<=obdfilter\.).*(?=-OST)'
        elif self.node_type.lower() == 'oss':
            param_regex = OSS_JOBSTATS_PARAM_REGEX
            # mdt.<filesystem>-MDT0000.job_stats
            filesystem_regex = r'(?<=mds\.).*(?=-MDT)'
        elif self.node_type.lower() == 'client':
            param_regex = 'llite.*.stats'
            # llite.<filesystem>-<device_uuid>.stats
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
        cmd = f'{"sudo " if sudo else ""}{bin} {" ".join(args)}'
        try:
            self.log.debug(f'Running command: {cmd}')
            output = subprocess.run(cmd, timeout=5, shell=True, capture_output=True, text=True)
            if output.stdout is None:
                self.log.debug(f'Command {cmd} returned no output, check if dd-agent is running with sufficient permissions. Captured stderr: {output.stderr}')
                return ''
            return output.stdout
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
            if jobstats_metrics is None:
                self.log.debug(f'No jobstats metrics found for {jobstats_param}')
                continue
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
        lnet_stats = self.run_command(self.lnetctl_path, stats_type, 'show', '-v', self.lnetctl_verbosity, sudo=True)
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
                status = 1 if ni.get('status') == 'up' else 0
                tags = self.tags + [f'net_type:{net_type}', f'nid:{nid}']
                self.gauge(f'net.local.status', status, tags=tags)
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
                tags = self.tags + [f'nid:{nid}', f'peer_nid:{peer_nid}']
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
            if self.node_type not in param.node_types:
                self.log.debug(f'Skipping param {param.regex} for node type {self.node_type}')
                continue
            if not param.regex.endswith('.stats'):
                continue
            param_list = self.run_command(self.lctl_path, "list_param", param.regex, sudo=True)
            for param_name in param_list.splitlines():
                tags = self.tags + self._extract_tags_from_param(param.regex, param_name, param.wildcards)
                raw_stats = self.run_command(self.lctl_path, "get_param", "-ny", param.regex, sudo=True)
                parsed_stats = self.parse_stats(raw_stats)
                for stat_name, stat_value in parsed_stats.items():
                    if isinstance(stat_value, int):
                        self.gauge(f'general.{stat_name}', stat_value, tags=tags)
                        continue
                    if not isinstance(stat_value, dict):
                        self.log.debug(f'Unexpected stat value for {stat_name}: {stat_value}')
                        continue
                    for metric_type, metric_value in stat_value.items():
                        if isinstance(metric_value, int):
                            self.gauge(f'general.{param.prefix}.{stat_name}.{metric_type}', metric_value, tags=tags)
                        else:
                            self.log.debug(f'Unexpected metric value for {stat_name}.{metric_type}: {metric_value}')

    def _extract_tags_from_param(self, param_regex, param_name, wildcards):
        '''
        Extract tags from the parameter name based on the regex and wildcard meanings.
        '''
        tags = []
        if wildcards:
            regex_parts = param_regex.split('.')
            param_parts = param_name.split('.')
            wildcard_number = 0
            if not len(regex_parts) == len(param_parts):
                self.log.debug(f'Parameter name {param_name} does not match regex {param_regex}')
                return tags
            for part_number, part in enumerate(regex_parts):
                if part == '*':
                    if wildcard_number >= len(wildcards):
                        self.log.debug(f'Found {wildcard_number} wildcards, which exceeds available wildcard tags {wildcards}')
                        return tags
                    tags.append(f'{wildcards[wildcard_number]}:{param_parts[part_number]}')
                    wildcard_number += 1
        return tags

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
                stat_value = {"count": int(parts[1])}
                # unit =  parts[3].strip('[]')
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
                ]
                tags += self.tags
                
                self.gauge('device.health', device_status, tags=tags)
                self.gauge('device.refcount', device['refcount'], tags=tags)
                
        except Exception as e:
            self.log.error(f'Failed to submit device health metrics: {e}')
    
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
                    date_time = parts[3] + ' ' + parts[2]
                    # The time has nanoseconds, so we need to truncate the last three digits
                    timestamp = time.mktime(time.strptime(date_time[:-3], '%Y.%m.%d %H:%M:%S.%f'))
                    data = {
                        'operation_type': parts[1],
                        'timestamp': timestamp,
                        'flags': parts[4],
                        'message': ' '.join(parts[5:])
                    }
                except IndexError:
                    self.log.debug(f'Unexpected changelog format: {line}')
                    continue
                self.send_log(data, {'index': parts[0]}, stream=target)

    def get_changelog(self, target):
        self.log.info(f'Collecting changelogs for: {target}')
        cursor = self.get_log_cursor(stream=target) 
        start_index = '0' if cursor is None else cursor['index']
        end_index = str(int(start_index) + self.changelog_lines_per_check)
        self.log.debug(f'Fetching changelog from index {start_index} to {end_index} for target {target}')
        return self.run_command(self.lfs_path, 'changelog', target, start_index, end_index, sudo=True)
