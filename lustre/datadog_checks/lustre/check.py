# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import subprocess
from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any, Dict, List, Set, Tuple, Union

import yaml

from datadog_checks.base import AgentCheck, is_affirmative

from .constants import (
    CURATED_PARAMS,
    DEFAULT_STATS,
    DEVICE_ATTR_NAMES,
    EXTRA_STATS,
    FILESYSTEM_DISCOVERY_PARAM_MAPPING,
    IGNORED_LNET_GROUPS,
    IGNORED_STATS,
    JOBID_TAG_PARAMS,
    JOBSTATS_PARAMS,
    TAGS_WITH_FILESYSTEM,
    LustreParam,
)

RATE_UNITS: Set[str] = {'locks/s'}


class IgnoredFilesystemName(Exception):
    pass


def _get_stat_type(suffix: str, unit: str) -> str:
    """
    Returns the metric type for a given stat suffix and unit.
    """
    if suffix == 'count':
        return 'count'
    elif suffix == 'bucket':
        return 'histogram'
    elif unit in RATE_UNITS:
        return 'rate'
    else:
        return 'gauge'


def _handle_ip_in_param(parts: List[str]) -> Tuple[List[str], bool]:
    """
    Merge parameter parts corresponding to an IP address.

    Example:
        ['some','172','0','0','12@tcp','param']
    =>  ['some','172.0.0.12@tcp', 'param']
    """
    match_indexes = [i for i in range(len(parts)) if '@' in parts[i]]
    if len(match_indexes) != 1 or match_indexes[0] < 3:
        return [], False
    index = match_indexes[0]
    new_part = ".".join(parts[index - 3 : index + 1])
    try:
        ip_address(new_part.split('@')[0])
    except ValueError:
        return [], False
    return [*parts[: index - 3], new_part, *parts[index + 1 :]], True


def _sanitize_command(bin_path: str) -> None:
    """
    Validate that the binary path is safe to execute.

    Ensures the path is absolute and is an expected Lustre binary.

    Raises:
        ValueError: If the path is not absolute or not an expected binary
    """
    # Allowlist of expected Lustre binaries
    EXPECTED_BINARIES = {'lctl', 'lnetctl', 'lfs'}

    # Check if the path is absolute
    if not os.path.isabs(bin_path):
        raise ValueError(f'Binary path must be absolute: {bin_path}')

    # Extract the binary name from the path
    binary_name = os.path.basename(bin_path)

    # Check if it's an expected Lustre binary
    if binary_name not in EXPECTED_BINARIES:
        raise ValueError(f'Unexpected binary: {binary_name}. Expected one of: {EXPECTED_BINARIES}')


class LustreCheck(AgentCheck):
    __NAMESPACE__ = 'lustre'

    def __init__(self, name: str, init_config: Dict[str, Any], instances: List[Dict[str, Any]]) -> None:
        super(LustreCheck, self).__init__(name, init_config, instances)

        # Paths to Lustre binaries
        lctl_path: str = self.instance.get('lctl_path', '/usr/sbin/lctl')
        lnetctl_path: str = self.instance.get('lnetctl_path', '/usr/sbin/lnetctl')
        lfs_path: str = self.instance.get('lfs_path', '/usr/bin/lfs')
        self._bin_mapping: Dict[str, str] = {'lctl': lctl_path, 'lnetctl': lnetctl_path, 'lfs': lfs_path}
        # Enable or disable specific metrics
        self.enable_changelogs: bool = is_affirmative(self.instance.get('enable_changelogs', False))
        self.lnetctl_verbosity: str = (
            '3' if is_affirmative(self.instance.get('enable_lnetctl_detailed', False)) else '1'
        )
        self.params: Set[LustreParam] = set(DEFAULT_STATS + CURATED_PARAMS)
        if is_affirmative(self.instance.get('enable_extra_params', False)):
            self.params.update(set(EXTRA_STATS))

        self.changelog_lines_per_check: int = int(self.instance.get('changelog_lines_per_check', 1000))

        self.devices: List[Dict[str, Any]] = []
        self.changelog_targets: List[str] = []
        self.filesystems: List[str] = self.instance.get('filesystems', [])
        # If filesystems were provided by the instance, do not update the filesystem list
        self.filesystem_discovery: bool = False if self.filesystems else True
        self._use_yaml: bool = True  # Older versions of Lustre (<2.15.5) do not support yaml as an output
        self.node_type: str = self.instance.get('node_type', self._find_node_type())

        self.tags: List[str] = self.instance.get('tags', [])
        self.tags.append(f'node_type:{self.node_type}')

    def _find_node_type(self) -> str:
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

    def check(self, _: Any) -> None:
        self.update()
        if self.node_type == 'client' and self.enable_changelogs:
            self.submit_changelogs(self.changelog_lines_per_check)

        self.submit_device_health(self.devices)
        self.submit_param_data(self.params)
        self.submit_lnet_stats_metrics()
        self.submit_lnet_local_ni_metrics()
        self.submit_lnet_peer_ni_metrics()

        if self.node_type in ('mds', 'oss'):
            self.submit_jobstats_metrics()

    def update(self) -> None:
        '''
        Update the check by finding devices and filesystems.
        '''
        self.log.debug('Updating Lustre check...')
        self._update_devices()
        if self.filesystem_discovery:
            self._update_filesystems()
        self._update_changelog_targets(self.devices, self.filesystems)
        self._update_metadata()

    def _update_devices(self) -> None:
        '''
        Find devices using the lctl dl command.
        '''
        self.log.debug('Updating device list...')
        devices = []
        if self._use_yaml:
            try:
                output = self._run_command('lctl', 'dl', '-y')
                device_data = yaml.safe_load(output)
                devices = device_data.get('devices', [])
            except AttributeError:
                self.log.debug('Device update failed with yaml flag, retrying without it.')
                self._use_yaml = False
        if not self._use_yaml:
            output = self._run_command('lctl', 'dl')
            for device_line in output.splitlines():
                device_attr = device_line.split()
                if not len(device_attr) == len(DEVICE_ATTR_NAMES):
                    self.log.error('Could not parse device info: %s', device_line)
                    continue
                devices.append(dict(zip(DEVICE_ATTR_NAMES, device_attr)))
        if not devices:
            self.log.error("No devices detected.")
            return
        self.devices = devices
        self.log.debug('Devices successfully updated.')

    def _update_filesystems(self) -> None:
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
            assert self.filesystems, f'Nothing matched regex `{filesystem_regex}` in params {lines}'
            self.log.debug('Found filesystem(s): %s', self.filesystems)
        except Exception as e:
            self.log.error('Failed to find filesystems: %s', e)
            return

    def _update_changelog_targets(self, devices: List[Dict[str, Any]], filesystems: List[str]) -> None:
        self.log.debug('Determining changelog targets...')
        target_regex = [re.escape(filesystem) + r'-MDT\d\d\d\d' for filesystem in filesystems]
        targets = []
        for device in devices:
            for regex in target_regex:
                match = re.search(regex, device['name'])
                if match:
                    targets.append(match.group(0))
        self.changelog_targets = list(set(targets))  # Remove duplicates

    @AgentCheck.metadata_entrypoint
    def _update_metadata(self):
        version = self._run_command("lctl", 'get_param', '-ny', 'version').strip()
        if version:
            self.log.debug("Setting version %s for Lustre", version)
            self.set_metadata("version", version)

    def _run_command(self, bin: str, *args: str, sudo: bool = False) -> str:
        '''
        Run a command using the given binary.
        '''
        if bin not in self._bin_mapping:
            raise ValueError('Unknown binary: {}'.format(bin))
        bin_path = self._bin_mapping[bin]
        _sanitize_command(bin_path)
        cmd = [bin_path, *args]
        if sudo:
            cmd.insert(0, "sudo")
        try:
            self.log.debug('Running command: %s', cmd)
            output = subprocess.run(
                cmd, timeout=5, shell=False, capture_output=True, text=True
            )  # Explicitly disable shell invocation to prevent command injection
            if not output.returncode == 0 and output.stderr:
                self.log.debug(
                    'Command %s exited with returncode %s. Captured stderr: %s', cmd, output.returncode, output.stderr
                )
                return ''
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

    def submit_jobstats_metrics(self) -> None:
        '''
        Submit the jobstats metrics to Datadog.

        For more information, see: https://doc.lustre.org/lustre_manual.xhtml#jobstats
        '''
        jobstats_param: LustreParam | None = None
        for param in JOBSTATS_PARAMS:
            if self.node_type in param.node_types:
                jobstats_param = param
                break
        if jobstats_param is None:
            self.log.debug('Invalid jobstats device_type: %s', self.node_type)
            return
        param_names = self._get_jobstats_params_list(jobstats_param)
        jobid_config_tags = [
            f'{param.regex}:{self._run_command("lctl", "get_param", "-ny", param.regex, sudo=True).strip()}'
            for param in JOBID_TAG_PARAMS
        ]
        for param_name in param_names:
            try:
                tags = (
                    self.tags
                    + self._extract_tags_from_param(jobstats_param.regex, param_name, jobstats_param.wildcards)
                    + jobid_config_tags
                )
            except IgnoredFilesystemName:
                continue
            jobstats_metrics = self._get_jobstats_metrics(param_name).get('job_stats')
            if jobstats_metrics is None:
                self.log.debug('No jobstats metrics found for %s', param_name)
                continue
            for job in jobstats_metrics:
                job_id = job.get('job_id', "unknown")
                tags.append(f'job_id:{job_id}')
                for metric_name, metric_values in job.items():
                    if not isinstance(metric_values, dict):
                        continue
                    self._submit_jobstat(metric_name, metric_values, tags)

    def _submit_jobstat(self, name: str, values: Dict[str, Any], tags: List[str]) -> None:
        for suffix, value in values.items():
            if suffix == 'samples':
                suffix = 'count'
            elif suffix == 'hist':
                suffix = 'bucket'
            elif suffix == 'unit':
                continue
            metric_type = _get_stat_type(suffix, values['unit'])
            self._submit(f'job_stats.{name}.{suffix}', value, metric_type, tags=tags)

    def _get_jobstats_params_list(self, param) -> List[str]:
        '''
        Get the jobstats params from the command line.
        '''
        raw_params = self._run_command('lctl', 'list_param', param.regex, sudo=True)
        return [line.strip() for line in raw_params.splitlines() if line.strip()]

    def _get_jobstats_metrics(self, jobstats_param: str) -> Dict[str, Any]:
        '''
        Get the jobstats metrics for a given jobstats param.
        '''
        jobstats_output = self._run_command('lctl', 'get_param', '-ny', jobstats_param, sudo=True)
        try:
            return yaml.safe_load(jobstats_output) or {}
        except Exception as e:
            self.log.debug('Could not get data for "%s", caught exception: %s', jobstats_param, e)
            return {}

    def submit_lnet_stats_metrics(self) -> None:
        '''
        Submit the lnet stats metrics.
        '''
        lnet_metrics = self._get_lnet_metrics('stats')
        if 'statistics' not in lnet_metrics:
            self.log.debug('Could not find `statistics` property in the output of lnet stats. Output: %s', lnet_metrics)
            return
        lnet_metrics = lnet_metrics['statistics']
        for metric in lnet_metrics:
            if metric.endswith('_count') or metric == 'errors':
                metric_type = 'count'
            else:
                metric_type = 'gauge'
            self._submit(f'net.{metric}', lnet_metrics[metric], metric_type, tags=[f'node_type:{self.node_type}'])

    def submit_lnet_local_ni_metrics(self) -> None:
        '''
        Submit the lnet local ni metrics.
        '''
        lnet_local_stats = self._get_lnet_metrics('net')
        if 'net' not in lnet_local_stats:
            self.log.debug('Could not find `net` property in the output of lnet stats. Output: %s', lnet_local_stats)
            return
        lnet_local_stats = lnet_local_stats['net']
        for net in lnet_local_stats:
            net_type = net.get('net type')
            for ni in net.get('local NI(s)', []):
                local_nid = ni.get('nid')
                status = 1 if ni.get('status') == 'up' else 0
                tags = self.tags + [f'net_type:{net_type}', f'local_nid:{local_nid}']
                self._submit('net.local.status', status, 'gauge', tags=tags)
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    self._submit_lnet_metric_group('local', stats_group_name, stats_group, tags)

    def submit_lnet_peer_ni_metrics(self) -> None:
        '''
        Submit the lnet peer ni metrics.
        '''
        lnet_peer_stats = self._get_lnet_metrics('peer')
        if 'peer' not in lnet_peer_stats:
            self.log.debug('Could not find `peer` property in the output of lnet stats. Output: %s', lnet_peer_stats)
            return
        lnet_peer_stats = lnet_peer_stats['peer']
        for peer in lnet_peer_stats:
            nid = peer.get('primary nid')
            for ni in peer.get('peer ni', []):
                peer_nid = ni.get('nid')
                tags = self.tags + [f'nid:{nid}', f'peer_nid:{peer_nid}']
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    self._submit_lnet_metric_group('peer', stats_group_name, stats_group, tags)

    def _submit_lnet_metric_group(self, prefix: str, group_name: str, group: Dict[str, Any], tags: List[str]) -> None:
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
        if group_name in IGNORED_LNET_GROUPS:
            self.log.debug('Ignoring lnet group %s', group_name)
            return
        for metric_name, metric_value in group.items():
            metric_name = metric_name.replace(' ', '_')
            if isinstance(metric_value, int):
                if 'tunables' in group_name or metric_name in ('health_value', 'next_ping'):
                    metric_type = 'gauge'
                else:
                    metric_type = 'count'
                self._submit(f'net.{prefix}.{group_name}.{metric_name}', metric_value, metric_type, tags=tags)

    def _get_lnet_metrics(self, stats_type: str = 'stats') -> Dict[str, Any]:
        '''
        Get the lnet stats from the command line.
        '''
        lnet_stats = self._run_command('lnetctl', stats_type, 'show', '-v', self.lnetctl_verbosity, sudo=True)
        try:
            return yaml.safe_load(lnet_stats) or {}
        except Exception as e:
            self.log.debug('Could not get lnet %s, caught exception: %s', stats_type, e)
            return {}

    def submit_param_data(self, params: Set[LustreParam]) -> None:
        '''
        Submit general stats and metrics from Lustre parameters.
        '''
        for param in params:
            if self.node_type not in param.node_types:
                self.log.debug('Skipping param %s for node type %s', param.regex, self.node_type)
                continue
            matched_params = self._run_command('lctl', 'list_param', param.regex, sudo=True)
            for param_name in matched_params.splitlines():
                try:
                    tags = self.tags + self._extract_tags_from_param(param.regex, param_name, param.wildcards)
                except IgnoredFilesystemName:
                    continue
                raw_stats = self._run_command('lctl', 'get_param', '-ny', param_name, sudo=True)
                if not param.regex.endswith('.stats'):
                    self._submit_param(param.prefix, param_name, tags)
                    continue
                parsed_stats = self._parse_stats(raw_stats)
                for stat_name, stat_value in parsed_stats.items():
                    self._submit_stat(param.prefix, stat_name, stat_value, tags)

    def _submit_param(self, prefix: str, param_name: str, tags: List[str]) -> None:
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

    def _submit_stat(self, prefix: str, name: str, value: Dict[str, Any], tags: List[str]) -> None:
        '''
        Submit a single stat metric.
        Usually the value is a dictionaty with a count, min, max, sum, and sumsq.
        '''
        for suffix, metric_value in value.items():
            if suffix == 'unit':
                continue
            if isinstance(metric_value, int):
                metric_type = _get_stat_type(suffix, value['unit'])
                self._submit(f'{prefix}.{name}.{suffix}', metric_value, metric_type, tags=tags)
            else:
                self.log.debug('Unexpected metric value for %s.%s: %s', name, suffix, metric_value)

    def _extract_tags_from_param(self, param_regex: str, param_name: str, wildcards: Tuple[str, ...]) -> List[str]:
        '''
        Extract tags from the parameter name based on the regex and wildcard meanings.
        '''
        if not wildcards:
            return []
        tags = []
        regex_parts = param_regex.split('.')
        param_parts = param_name.split('.')
        wildcard_generator = (wildcard for wildcard in wildcards)
        filesystem = None
        if not len(regex_parts) == len(param_parts):
            # Edge case: mdt.lustre-MDT0000.exports.172.31.16.218@tcp.stats
            if len(regex_parts) + 3 == len(param_parts):
                # We need to reconstruct the address
                param_parts, is_valid_ip = _handle_ip_in_param(param_parts)
                if not is_valid_ip:
                    self.log.debug("Skipping tags for parameter %s", param_name)
                    return []
            else:
                self.log.debug('Parameter name %s does not match regex %s', param_name, param_regex)
                return tags
        for part_number, part in enumerate(regex_parts):
            if part == '*':
                try:
                    current_wildcard = next(wildcard_generator)
                    current_part = param_parts[part_number]
                    tags.append(f'{current_wildcard}:{current_part}')
                    if current_wildcard in TAGS_WITH_FILESYSTEM and filesystem is None:
                        filesystem = current_part.split('-')[0]
                        tags.append(f'filesystem:{filesystem}')
                        self.log.debug('Determined filesystem as %s from parameter %s', filesystem, param_name)
                        if filesystem not in self.filesystems:
                            self.log.debug('Skipping param %s as it did not match any filesystem', param_name)
                            raise IgnoredFilesystemName
                except StopIteration:
                    self.log.debug('Number of found wildcards exceeds available wildcard tags %s', wildcards)
                    return tags
        return tags

    def _parse_stats(self, raw_stats: str) -> Dict[str, Dict[str, Union[int, str]]]:
        '''
        Parse the raw stats into a dictionary.

        Expected format:
            elapsed_time              2068792.478877751 secs.nsecs
            req_waittime              83 samples [usecs] 11 40 1493 32135
            req_qdepth                83 samples [reqs] 0 0 0 0
            cancel                    253 samples [locks] 1 1 253
            tgtreg                    2 samples [reqs]
        '''
        stats: Dict[str, Dict[str, Union[int, str]]] = {}
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
                stat_dict: Dict[str, Union[int, str]] = {'count': int(parts[1])}
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

    def submit_device_health(self, devices: List[Dict[str, Any]]) -> None:
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

    def submit_changelogs(self, lines: int) -> None:
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
                    timestamp = (
                        datetime.strptime(date_time[:-3], '%Y.%m.%d %H:%M:%S.%f')
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                    )
                    data = {
                        'operation_type': parts[1],
                        'timestamp': timestamp,
                        'flags': parts[4],
                        'message': ' '.join(parts[5:]),
                    }
                except IndexError:
                    self.log.debug('Skipping changelog due to unexpected format: %s', line)
                    continue
                next_index = int(parts[0]) + 1
                self.send_log(data, {'index': str(next_index)}, stream=target)

    def _get_changelog(self, target: str, lines: int) -> str:
        '''
        Get the changelog for a given target.

        Expected format:
            22 14SATTR 12:51:02.232953392 2025.06.02 0x14 t=[0x200000bd1:0x8:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp
            23 11CLOSE 12:51:02.238364514 2025.06.02 0x1 t=[0x200000bd1:0x5:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp
        '''
        self.log.info('Collecting changelogs for: %s', target)
        try:
            cursor = self.get_log_cursor(stream=target)
        except Exception as e:
            self.log.info('Could not retrieve log cursor, assuming initialization. Captured error: %s', e)
            cursor = {'index': '0'}
        start_index = '0' if cursor is None else cursor['index']
        end_index = str(int(start_index) + lines)
        self.log.debug('Fetching changelog from index %s to %s for target %s', start_index, end_index, target)
        return self._run_command('lfs', 'changelog', target, start_index, end_index, sudo=True)

    def _submit(self, name: str, value: Union[int, float, Dict[str, Any]], metric_type: str, tags: List[str]) -> None:
        """
        Submits a single metric.
        """
        if metric_type == 'gauge':
            self.gauge(name, value, tags=tags)
        elif metric_type == 'rate':
            self.rate(name, value, tags=tags)
        elif metric_type == 'count':
            self.monotonic_count(name, value, tags=tags)
        elif metric_type == 'histogram':
            if not isinstance(value, Dict):
                self.log.debug("Unexpected value for metric type histogram: %s", value)
                return
            cumulative_count = 0
            previous_bucket = 0
            for bucket, count in value.items():
                cumulative_count += count
                self.monotonic_count(
                    name, cumulative_count, tags=tags + [f'upper_bound:{bucket}', f'lower_bound:{previous_bucket}']
                )
                previous_bucket = bucket
            self.monotonic_count(
                name, cumulative_count, tags=tags + ['upper_bound:+Inf', f'lower_bound:{previous_bucket}']
            )
