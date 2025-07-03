# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import subprocess
import time
from typing import Any  # noqa: F401

import yaml

from datadog_checks.base import AgentCheck, is_affirmative  # noqa: F401

from .constants import (
    CURATED_PARAMS,
    DEFAULT_STATS,
    EXTRA_STATS,
    FILESYSTEM_DISCOVERY_PARAM_MAPPING,
    IGNORED_LNET_GROUPS,
    IGNORED_STATS,
    JOBSTATS_PARAMS,
)

RATE_UNITS = {'locks/s'}


def _get_stat_type(suffix, unit):
    """
    Returns the metric type for a given stat suffix and unit.
    """
    if suffix == 'count':
        return 'count'
    elif unit in RATE_UNITS:
        return 'rate'
    else:
        return 'gauge'


def _handle_ip_in_param(parts):
    match_index = 0
    for i, part in enumerate(parts):
        if '@' in part:
            match_index = i
    new_part = ".".join(parts[match_index - 3 : match_index + 1])
    return [*parts[: match_index - 3], new_part, *parts[match_index + 1 :]]


class LustreCheck(AgentCheck):
    __NAMESPACE__ = 'lustre'

    def __init__(self, name, init_config, instances):
        super(LustreCheck, self).__init__(name, init_config, instances)

        # Paths to Lustre binaries
        lctl_path = self.instance.get('lctl_path', '/usr/sbin/lctl')
        lnetctl_path = self.instance.get('lnetctl_path', '/usr/sbin/lnetctl')
        lfs_path = self.instance.get('lfs_path', '/usr/bin/lfs')
        self._bin_mapping = {'lctl': lctl_path, 'lnetctl': lnetctl_path, 'lfs': lfs_path}
        # Enable or disable specific metrics
        self.enable_changelogs = is_affirmative(self.instance.get('enable_changelogs', False))
        self.lnetctl_verbosity = '3' if is_affirmative(self.instance.get('enable_lnetctl_detailed', False)) else '1'
        self.param_list = set(DEFAULT_STATS + CURATED_PARAMS)
        if is_affirmative(self.instance.get('enable_extra_params', False)):
            self.param_list.update(set(EXTRA_STATS))

        self.changelog_lines_per_check = int(self.instance.get('changelog_lines_per_check', 1000))

        self.devices = []
        self.changelog_targets = []
        self.filesystems = self.instance.get('filesystems', [])
        # If filesystems were provided by the instance, do not update the filesystem list
        self.filesystem_discovery = False if self.filesystems else True
        self.node_type = self.instance.get('node_type', self._find_node_type())

        self.tags = self.instance.get('tags', [])
        self.tags.append(f'node_type:{self.node_type}')
        version = self._run_command("lctl", 'get_param', '-ny', 'version').strip()
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
            self.log.error('Failed to determine node type: %s', e)
            return 'client'

    def check(self, _):
        self.update()
        if self.node_type == 'client' and self.enable_changelogs:
            self.submit_changelogs(self.changelog_lines_per_check)

        self.submit_device_health(self.devices)
        self.submit_param_data(self.param_list)
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
        if self.filesystem_discovery:
            self._update_filesystems()
        self._update_changelog_targets(self.devices, self.filesystems)

    def _update_devices(self):
        '''
        Find devices using the lctl dl command.
        '''
        self.log.debug('Updating device list...')
        output = self._run_command('lctl', 'dl', '-y')
        device_data = yaml.safe_load(output)
        self.devices = device_data.get('devices', [])

    def _update_filesystems(self):
        '''
        Find filesystems using the lctl list_param command.
        '''
        self.log.debug('Finding filesystems...')
        if self.node_type not in FILESYSTEM_DISCOVERY_PARAM_MAPPING:
            self.log.debug('Invalid node_type: %s', self.node_type)
            return
        param_regex, filesystem_regex = FILESYSTEM_DISCOVERY_PARAM_MAPPING[self.node_type]
        try:
            raw_output = self._run_command('lctl', 'list_param', param_regex, sudo=True)
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
            self.log.debug('Found filesystem(s): %s', self.filesystems)
        except Exception as e:
            self.log.error('Failed to find filesystems: %s', e)
            return

    def _update_changelog_targets(self, devices, filesystems):
        self.log.debug('Determining changelog targets...')
        target_regex = [filesystem + r'-MDT\d\d\d\d' for filesystem in filesystems]
        targets = []
        for device in devices:
            for regex in target_regex:
                match = re.search(regex, device['name'])
                if match:
                    targets.append(match.group(0))
        self.changelog_targets = list(set(targets))  # Remove duplicates

    def _run_command(self, bin, *args, sudo=False):
        '''
        Run a command using the given binary.
        '''
        if bin not in self._bin_mapping:
            raise ValueError('Unknown binary: {}'.format(bin))
        bin_path = self._bin_mapping[bin]
        cmd = f'{"sudo " if sudo else ""}{bin_path} {" ".join(args)}'
        try:
            self.log.debug('Running command: %s', cmd)
            output = subprocess.run(cmd, timeout=5, shell=True, capture_output=True, text=True)
            if output.stdout is None:
                self.log.debug(
                    'Command %s returned no output, check if dd-agent is running\
                    with sufficient permissions. Captured stderr: %s',
                    cmd,
                    output.stderr,
                )
                return ''
            return output.stdout
        except Exception as e:
            self.log.error('Failed to run command %s: %s', cmd, e)
            return ''

    def submit_jobstats_metrics(self):
        '''
        Submit the jobstats metrics to Datadog.

        For more information, see: https://doc.lustre.org/lustre_manual.xhtml#jobstats
        '''
        jobstats_params = self._get_jobstats_params_list()
        for jobstats_param in jobstats_params:
            device_name = jobstats_param.split('.')[1]  # For example: lustre-MDT0000
            if self.filesystems and not any(device_name.startswith(filesystem) for filesystem in self.filesystems):
                continue
            jobstats_metrics = self._get_jobstats_metrics(jobstats_param)['job_stats']
            if jobstats_metrics is None:
                self.log.debug('No jobstats metrics found for %s', jobstats_param)
                continue
            for job in jobstats_metrics:
                job_id = job['job_id']
                tags = [f'device_name:{device_name}', f'job_id:{job_id}']
                for metric_name, metric_values in job.items():
                    self._submit_jobstat(metric_name, metric_values, tags)

    def _submit_jobstat(self, name, values, tags):
        if not isinstance(values, dict):
            return
        for suffix, value in values.items():
            if suffix == 'samples':
                suffix = 'count'
            if suffix == 'unit':
                continue
            if suffix == 'hist':
                # TODO: Handle histogram metrics if needed
                continue
            metric_type = _get_stat_type(suffix, values['unit'])
            self._submit(f'job_stats.{name}.{suffix}', value, metric_type, tags=tags)

    def _get_jobstats_params_list(self):
        '''
        Get the jobstats params from the command line.
        '''
        param = None
        for jobstat_param in JOBSTATS_PARAMS:
            if self.node_type in jobstat_param.node_types:
                param = jobstat_param
                break
        if param is None:
            self.log.debug('Invalid jobstats device_type: %s', self.node_type)
            return []
        raw_params = self._run_command('lctl', 'list_param', param.regex, sudo=True)
        return [line.strip() for line in raw_params.splitlines() if line.strip()]

    def _get_jobstats_metrics(self, jobstats_param):
        '''
        Get the jobstats metrics for a given jobstats param.
        '''
        jobstats_output = self._run_command('lctl', 'get_param', '-ny', jobstats_param, sudo=True)
        try:
            return yaml.safe_load(jobstats_output) or {}
        except KeyError:
            self.log.debug('No jobstats metrics found for %s', jobstats_param)
            return {}

    def submit_lnet_stats_metrics(self):
        '''
        Submit the lnet stats metrics.
        '''
        lnet_metrics = self._get_lnet_metrics('stats')['statistics']
        for metric in lnet_metrics:
            if metric.endswith('_count') or metric == 'errors':
                metric_type = 'count'
            else:
                metric_type = 'gauge'
            self._submit(f'net.{metric}', lnet_metrics[metric], metric_type, tags=[f'node_type:{self.node_type}'])

    def submit_lnet_local_ni_metrics(self):
        '''
        Submit the lnet local ni metrics.
        '''
        lnet_local_stats = self._get_lnet_metrics('net')['net']
        for net in lnet_local_stats:
            net_type = net.get('net type')
            for ni in net.get('local NI(s)', []):
                local_nid = ni.get('nid')
                status = 1 if ni.get('status') == 'up' else 0
                tags = self.tags + [f'net_type:{net_type}', f'local_nid:{local_nid}']
                self._submit('net.local.status', status, 'gauge', tags=tags)
                for stats_group_name, stats_group in ni.items():
                    self._submit_lnet_metric_group('local', stats_group_name, stats_group, tags)

    def submit_lnet_peer_ni_metrics(self):
        '''
        Submit the lnet peer ni metrics.
        '''
        lnet_peer_stats = self._get_lnet_metrics('peer')['peer']
        for peer in lnet_peer_stats:
            nid = peer.get('primary nid')
            for ni in peer.get('peer ni', []):
                peer_nid = ni.get('nid')
                tags = self.tags + [f'nid:{nid}', f'peer_nid:{peer_nid}']
                for stats_group_name, stats_group in ni.items():
                    self._submit_lnet_metric_group('peer', stats_group_name, stats_group, tags)

    def _submit_lnet_metric_group(self, prefix, group_name, group, tags):
        '''
        Submit a group of lnet metrics.

        Groups represent a set of metrics, for example:
            health stats:
                  health value: 1000
                  dropped: 0
                  timeout: 0
                  error: 0
                  network timeout: 4
                  ping_count: 0
                  next_ping: 0
        '''
        group_name = group_name.replace(' ', '_')
        if not isinstance(group, dict):
            return
        if group_name in IGNORED_LNET_GROUPS:
            self.log.debug('Ignoring lnet group %s', group_name)
            return
        for metric_name, metric_value in group.items():
            metric_name = metric_name.replace(' ', '_')
            if isinstance(metric_value, int):
                if group_name == 'tunables' or metric_name in ('health_value', 'next_ping'):
                    metric_type = 'gauge'
                else:
                    metric_type = 'count'
                self._submit(f'net.{prefix}.{group_name}.{metric_name}', metric_value, metric_type, tags=tags)

    def _get_lnet_metrics(self, stats_type='stats'):
        '''
        Get the lnet stats from the command line.
        '''
        lnet_stats = self._run_command('lnetctl', stats_type, 'show', '-v', self.lnetctl_verbosity, sudo=True)
        try:
            return yaml.safe_load(lnet_stats)
        except (KeyError, ValueError):
            self.log.debug('No lnet stats found')
            return {}

    def submit_param_data(self, param_list):
        '''
        Submit general stats and metrics from Lustre parameters.
        '''
        for param in param_list:
            if self.node_type not in param.node_types:
                self.log.debug('Skipping param %s for node type %s', param.regex, self.node_type)
                continue
            matched_params = self._run_command('lctl', 'list_param', param.regex, sudo=True)
            for param_name in matched_params.splitlines():
                tags = self.tags + self._extract_tags_from_param(param.regex, param_name, param.wildcards)
                raw_stats = self._run_command('lctl', 'get_param', '-ny', param_name, sudo=True)
                if not param.regex.endswith('.stats'):
                    self._submit_param(param.prefix, param_name, tags)
                    continue
                parsed_stats = self._parse_stats(raw_stats)
                for stat_name, stat_value in parsed_stats.items():
                    self._submit_stat(param.prefix, stat_name, stat_value, tags)

    def _submit_param(self, prefix, param_name, tags):
        '''
        Submit a single parameter.
        '''
        try:
            output = int(self._run_command('lctl', 'get_param', '-ny', param_name, sudo=True))
            suffix = param_name.split('.')[-1]
        except (ValueError, TypeError):
            self.log.debug('No output found for %s', param_name)
            return
        self._submit(f'{prefix}.{suffix}', output, 'gauge', tags=tags)

    def _submit_stat(self, prefix, name, value, tags):
        '''
        Submit a single stat metric.
        Usually the value is a dictionaty with a count, min, max, sum, and sumsq.
        '''
        if not isinstance(value, dict):
            self.log.debug('Unexpected stat value for %s: %s', name, value)
            return
        for suffix, metric_value in value.items():
            if suffix == 'unit':
                continue
            if isinstance(metric_value, int):
                metric_type = _get_stat_type(suffix, value['unit'])
                self._submit(f'{prefix}.{name}.{suffix}', metric_value, metric_type, tags=tags)
            else:
                self.log.debug('Unexpected metric value for %s.%s: %s', name, suffix, metric_value)

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
                # Edge case: mdt.lustre-MDT0000.exports.172.31.16.218@tcp.stats
                if any("@" in part for part in param_parts):
                    # We need to reconstruct the address
                    param_parts = _handle_ip_in_param(param_parts)
                else:
                    self.log.debug('Parameter name %s does not match regex %s', param_name, param_regex)
                    return tags
            for part_number, part in enumerate(regex_parts):
                if part == '*':
                    if wildcard_number >= len(wildcards):
                        self.log.debug(
                            'Found %s wildcards, which exceeds available wildcard tags %s', wildcard_number, wildcards
                        )
                        return tags
                    tags.append(f'{wildcards[wildcard_number]}:{param_parts[part_number]}')
                    wildcard_number += 1
        return tags

    def _parse_stats(self, raw_stats):
        '''
        Parse the raw stats into a dictionary.

        Expected format:
            elapsed_time              2068792.478877751 secs.nsecs
            req_waittime              83 samples [usecs] 11 40 1493 32135
            req_qdepth                83 samples [reqs] 0 0 0 0
            cancel                    253 samples [locks] 1 1 253
            tgtreg                    2 samples [reqs]
        '''
        stats = {}
        for line in raw_stats.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            stat_name = parts[0]
            if stat_name in IGNORED_STATS:
                continue
            try:
                stat_dict = {'count': int(parts[1])}
                stat_types = ('min', 'max', 'sum', 'sumsq')
                if len(parts) < 3:
                    self.log.debug('Unexpected format for stat "%s"', line)
                    continue
                stat_dict['unit'] = parts[3].strip('[]')
                for i, value in enumerate(parts[4:]):
                    stat_dict[stat_types[i]] = int(value)
                if len(parts) > 8:
                    self.log.debug('Unexpected format for stat "%s"', line)
            except ValueError:
                self.log.debug('Could not parse stat value for "%s"', line)
                continue
            stats[stat_name] = stat_dict
        return stats

    def submit_device_health(self, devices):
        '''
        Submit device health metrics based on device status from lctl dl command.
        '''
        try:
            for device in devices:
                device_status = 1 if device['status'] == 'UP' else 0
                tags = [
                    f'device_type:{device.get("type", "unknown")}',
                    f'device_name:{device.get("name", "unknown")}',
                    f'device_uuid:{device.get("uuid", "unknown")}',
                ]
                tags += self.tags

                self._submit('device.health', device_status, 'gauge', tags=tags)
                self._submit('device.refcount', device['refcount'], 'count', tags=tags)
        except Exception as e:
            self.log.error('Failed to submit device health metrics: %s', e)

    def submit_changelogs(self, lines):
        '''
        Get changelogs from the command line.

        For more information, see: https://doc.lustre.org/lustre_manual.xhtml#lustre_changelogs
        '''
        for target in self.changelog_targets:
            changelog = self._get_changelog(target, lines)
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
                        'message': ' '.join(parts[5:]),
                    }
                except IndexError:
                    self.log.debug('Unexpected changelog format: %s', line)
                    continue
                self.send_log(data, {'index': parts[0]}, stream=target)

    def _get_changelog(self, target, lines):
        '''
        Get the changelog for a given target.

        Expected format:
            22 14SATTR 12:51:02.232953392 2025.06.02 0x14 t=[0x200000bd1:0x8:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp
            23 11CLOSE 12:51:02.238364514 2025.06.02 0x1 t=[0x200000bd1:0x5:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp
        '''
        self.log.info('Collecting changelogs for: %s', target)
        cursor = self.get_log_cursor(stream=target)
        start_index = '0' if cursor is None else cursor['index']
        end_index = str(int(start_index) + lines)
        self.log.debug('Fetching changelog from index %s to %s for target %s', start_index, end_index, target)
        return self._run_command('lfs', 'changelog', target, start_index, end_index, sudo=True)

    def _submit(self, name, value, metric_type, tags):
        """
        Submits a single metric.
        """
        if metric_type == 'gauge':
            self.gauge(name, value, tags=tags)
        elif metric_type == 'rate':
            self.rate(name, value, tags=tags)
        elif metric_type == 'count':
            self.count(name, value, tags=tags)
        elif metric_type == 'histogram':
            # TODO: handle this case
            return
