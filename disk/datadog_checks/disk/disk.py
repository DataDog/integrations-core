# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import platform
import re

from six import iteritems, string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import get_subprocess_output
from datadog_checks.base.utils.timeout import TimeoutException, timeout

try:
    import psutil
except ImportError:
    psutil = None

try:
    import datadog_agent  # noqa: F401

    is_agent_6 = True
except ImportError:
    is_agent_6 = False


IGNORE_CASE = re.I if platform.system() == 'Windows' else 0


class Disk(AgentCheck):
    """ Collects metrics about the machine's disks. """

    # -T for filesystem info
    DF_COMMAND = ['df', '-T']
    METRIC_DISK = 'system.disk.{}'
    METRIC_INODE = 'system.fs.inodes.{}'

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Disk check only supports one configured instance.')
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)

        instance = instances[0]
        self._all_partitions = is_affirmative(instance.get('all_partitions', False))
        self._file_system_whitelist = instance.get('file_system_whitelist', [])
        self._file_system_blacklist = instance.get('file_system_blacklist', [])
        self._device_whitelist = instance.get('device_whitelist', [])
        self._device_blacklist = instance.get('device_blacklist', [])
        self._mount_point_whitelist = instance.get('mount_point_whitelist', [])
        self._mount_point_blacklist = instance.get('mount_point_blacklist', [])
        self._tag_by_filesystem = is_affirmative(instance.get('tag_by_filesystem', False))
        self._device_tag_re = instance.get('device_tag_re', {})
        self._custom_tags = instance.get('tags', [])
        self._service_check_rw = is_affirmative(instance.get('service_check_rw', False))

        # TODO Remove this v5/v6 fork when agent 5 will be fully deprecated
        if is_agent_6:
            self._use_mount = is_affirmative(instance.get('use_mount', False))
        else:
            # FIXME: 6.x, drop use_mount option in datadog.conf
            self._load_legacy_option(instance, 'use_mount', False, operation=is_affirmative)

            # FIXME: 6.x, drop device_blacklist_re option in datadog.conf
            self._load_legacy_option(
                instance, 'excluded_disk_re', '^$', legacy_name='device_blacklist_re', operation=re.compile
            )
        self._compile_pattern_filters(instance)
        self._compile_tag_re()

    def _load_legacy_option(self, instance, option, default, legacy_name=None, operation=lambda l: l):
        value = instance.get(option, default)
        legacy_name = legacy_name or option

        if value == default and legacy_name in self.agentConfig:
            self.log.warning(
                'Using `{}` in datadog.conf has been deprecated '
                'in favor of `{}` in disk.yaml'.format(legacy_name, option)
            )
            value = self.agentConfig.get(legacy_name) or default

        setattr(self, '_{}'.format(option), operation(value))

    def check(self, instance):
        """Get disk space/inode stats"""
        # Windows and Mac will always have psutil
        # (we have packaged for both of them)
        if self._psutil():
            self.collect_metrics_psutil()
        else:
            # FIXME: implement all_partitions (df -a)
            self.collect_metrics_manually()

    @classmethod
    def _psutil(cls):
        return psutil is not None

    def collect_metrics_psutil(self):
        self._valid_disks = {}
        for part in psutil.disk_partitions(all=True):
            # we check all exclude conditions
            if self.exclude_disk(part):
                continue

            # Get disk metrics here to be able to exclude on total usage
            try:
                disk_usage = timeout(5)(psutil.disk_usage)(part.mountpoint)
            except TimeoutException:
                self.log.warning(
                    u'Timeout while retrieving the disk usage of `%s` mountpoint. Skipping...', part.mountpoint
                )
                continue
            except Exception as e:
                self.log.warning('Unable to get disk metrics for %s: %s', part.mountpoint, e)
                continue

            # Exclude disks with total disk size 0
            if disk_usage.total == 0:
                continue

            # For later, latency metrics
            self._valid_disks[part.device] = (part.fstype, part.mountpoint)
            self.log.debug('Passed: {}'.format(part.device))

            device_name = part.mountpoint if self._use_mount else part.device

            tags = [part.fstype, 'filesystem:{}'.format(part.fstype)] if self._tag_by_filesystem else []
            tags.extend(self._custom_tags)

            # apply device/mountpoint specific tags
            for regex, device_tags in self._device_tag_re:
                if regex.match(device_name):
                    tags.extend(device_tags)

            # legacy check names c: vs psutil name C:\\
            if Platform.is_win32():
                device_name = device_name.strip('\\').lower()

            tags.append('device:{}'.format(device_name))
            for metric_name, metric_value in iteritems(self._collect_part_metrics(part, disk_usage)):
                self.gauge(metric_name, metric_value, tags=tags)

            # Add in a disk read write or read only check
            if self._service_check_rw:
                rwro = {'rw', 'ro'} & set(part.opts.split(','))
                if len(rwro) == 1:
                    self.service_check(
                        'disk.read_write', AgentCheck.OK if rwro.pop() == 'rw' else AgentCheck.CRITICAL, tags=tags
                    )
                else:
                    self.service_check('disk.read_write', AgentCheck.UNKNOWN, tags=tags)

        self.collect_latency_metrics()

    def exclude_disk(self, part):
        # skip cd-rom drives with no disk in it; they may raise
        # ENOENT, pop-up a Windows GUI error for a non-ready
        # partition or just hang;
        # and all the other excluded disks
        skip_win = Platform.is_win32() and ('cdrom' in part.opts or part.fstype == '')
        return skip_win or self._exclude_disk(part.device, part.fstype, part.mountpoint)

    def _exclude_disk(self, device, file_system, mount_point):
        """
        Return True for disks we don't want or that match regex in the config file
        """
        self.log.debug('_exclude_disk: {}, {}, {}'.format(device, file_system, mount_point))

        if not device or device == 'none':
            device = None

            # Allow no device if `all_partitions` is true so we can evaluate mount points
            if not self._all_partitions:
                return True

        # Hack for NFS secure mounts
        # Secure mounts might look like this: '/mypath (deleted)', we should
        # ignore all the bits not part of the mount point name. Take also into
        # account a space might be in the mount point.
        mount_point = mount_point.rsplit(' ', 1)[0]

        return self._partition_blacklisted(device, file_system, mount_point) or not self._partition_whitelisted(
            device, file_system, mount_point
        )

    def _partition_whitelisted(self, device, file_system, mount_point):
        return (
            self._file_system_whitelisted(file_system)
            and self._device_whitelisted(device)
            and self._mount_point_whitelisted(mount_point)
        )

    def _partition_blacklisted(self, device, file_system, mount_point):
        return (
            self._file_system_blacklisted(file_system)
            or self._device_blacklisted(device)
            or self._mount_point_blacklisted(mount_point)
        )

    def _file_system_whitelisted(self, file_system):
        if self._file_system_whitelist is None:
            return True

        return not not self._file_system_whitelist.match(file_system)

    def _file_system_blacklisted(self, file_system):
        if self._file_system_blacklist is None:
            return False

        return not not self._file_system_blacklist.match(file_system)

    def _device_whitelisted(self, device):
        if not device or self._device_whitelist is None:
            return True

        return not not self._device_whitelist.match(device)

    def _device_blacklisted(self, device):
        if not device or self._device_blacklist is None:
            return False

        return not not self._device_blacklist.match(device)

    def _mount_point_whitelisted(self, mount_point):
        if self._mount_point_whitelist is None:
            return True

        return not not self._mount_point_whitelist.match(mount_point)

    def _mount_point_blacklisted(self, mount_point):
        if self._mount_point_blacklist is None:
            return False

        return not not self._mount_point_blacklist.match(mount_point)

    def _collect_part_metrics(self, part, usage):
        metrics = {}

        for name in ['total', 'used', 'free']:
            # For legacy reasons,  the standard unit it kB
            metrics[self.METRIC_DISK.format(name)] = getattr(usage, name) / 1024

        # FIXME: 6.x, use percent, a lot more logical than in_use
        metrics[self.METRIC_DISK.format('in_use')] = usage.percent / 100

        if Platform.is_unix():
            metrics.update(self._collect_inodes_metrics(part.mountpoint))

        return metrics

    def _collect_inodes_metrics(self, mountpoint):
        metrics = {}
        # we need to timeout this, too.
        try:
            inodes = timeout(5)(os.statvfs)(mountpoint)
        except TimeoutException:
            self.log.warning(u'Timeout while retrieving the disk usage of `%s` mountpoint. Skipping...', mountpoint)
            return metrics
        except Exception as e:
            self.log.warning('Unable to get disk metrics for %s: %s', mountpoint, e)
            return metrics

        if inodes.f_files != 0:
            total = inodes.f_files
            free = inodes.f_ffree

            metrics[self.METRIC_INODE.format('total')] = total
            metrics[self.METRIC_INODE.format('free')] = free
            metrics[self.METRIC_INODE.format('used')] = total - free
            # FIXME: 6.x, use percent, a lot more logical than in_use
            metrics[self.METRIC_INODE.format('in_use')] = (total - free) / total

        return metrics

    def collect_latency_metrics(self):
        for disk_name, disk in iteritems(psutil.disk_io_counters(True)):
            self.log.debug('IO Counters: {} -> {}'.format(disk_name, disk))
            try:
                # x100 to have it as a percentage,
                # /1000 as psutil returns the value in ms
                read_time_pct = disk.read_time * 100 / 1000
                write_time_pct = disk.write_time * 100 / 1000
                metric_tags = [] if self._custom_tags is None else self._custom_tags[:]
                metric_tags.append('device:{}'.format(disk_name))
                self.rate(self.METRIC_DISK.format('read_time_pct'), read_time_pct, tags=metric_tags)
                self.rate(self.METRIC_DISK.format('write_time_pct'), write_time_pct, tags=metric_tags)
            except AttributeError as e:
                # Some OS don't return read_time/write_time fields
                # http://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
                self.log.debug('Latency metrics not collected for {}: {}'.format(disk_name, e))

    # no psutil, let's use df
    def collect_metrics_manually(self):
        df_out, _, _ = get_subprocess_output(self.DF_COMMAND + ['-k'], self.log)
        self.log.debug(df_out)

        for device in self._list_devices(df_out):
            self.log.debug("Passed: {}".format(device))
            device_name = device[-1] if self._use_mount else device[0]

            tags = [device[1], 'filesystem:{}'.format(device[1])] if self._tag_by_filesystem else []
            tags.extend(self._custom_tags)

            # apply device/mountpoint specific tags
            for regex, device_tags in self._device_tag_re:
                if regex.match(device_name):
                    tags += device_tags
            tags.append('device:{}'.format(device_name))
            for metric_name, value in iteritems(self._collect_metrics_manually(device)):
                self.gauge(metric_name, value, tags=tags)

    def _collect_metrics_manually(self, device):
        result = {}

        used = float(device[3])
        free = float(device[4])

        # device is
        # ["/dev/sda1", "ext4", 524288,  171642,  352646, "33%", "/"]
        result[self.METRIC_DISK.format('total')] = float(device[2])
        result[self.METRIC_DISK.format('used')] = used
        result[self.METRIC_DISK.format('free')] = free

        # Rather than grabbing in_use, let's calculate it to be more precise
        result[self.METRIC_DISK.format('in_use')] = used / (used + free)

        result.update(self._collect_inodes_metrics(device[-1]))
        return result

    def _keep_device(self, device):
        # device is for Unix
        # [/dev/disk0s2, ext4, 244277768, 88767396, 155254372, 37%, /]
        # First, skip empty lines.
        # then filter our fake hosts like 'map -hosts'.
        #    Filesystem    Type   1024-blocks     Used Available Capacity  Mounted on
        #    /dev/disk0s2  ext4     244277768 88767396 155254372    37%    /
        #    map -hosts    tmpfs            0        0         0   100%    /net
        # and finally filter out fake devices
        return (
            device
            and len(device) > 1
            and device[2].isdigit()
            and not self._exclude_disk(device[0], device[1], device[6])
        )

    def _flatten_devices(self, devices):
        # Some volumes are stored on their own line. Rejoin them here.
        previous = None
        for parts in devices:
            if len(parts) == 1:
                previous = parts[0]
            elif previous is not None:
                # collate with previous line
                parts.insert(0, previous)
                previous = None
            else:
                previous = None
        return devices

    def _list_devices(self, df_output):
        """
        Given raw output for the df command, transform it into a normalized
        list devices. A 'device' is a list with fields corresponding to the
        output of df output on each platform.
        """
        all_devices = [l.strip().split() for l in df_output.splitlines()]

        # Skip the header row and empty lines.
        raw_devices = [l for l in all_devices[1:] if l]

        # Flatten the disks that appear in the mulitple lines.
        flattened_devices = self._flatten_devices(raw_devices)

        # Filter fake or unwanteddisks.
        return [d for d in flattened_devices if self._keep_device(d)]

    def _compile_pattern_filters(self, instance):
        # Force exclusion of CDROM (iso9660)
        file_system_blacklist_extras = ['iso9660$']
        device_blacklist_extras = []
        mount_point_blacklist_extras = []

        deprecation_message = '`{old}` is deprecated and will be removed in 6.9. Please use `{new}` instead.'

        if 'excluded_filesystems' in instance:
            file_system_blacklist_extras.extend(
                '{}$'.format(pattern) for pattern in instance['excluded_filesystems'] if pattern
            )
            self.warning(deprecation_message.format(old='excluded_filesystems', new='file_system_blacklist'))

        if 'excluded_disks' in instance:
            device_blacklist_extras.extend('{}$'.format(pattern) for pattern in instance['excluded_disks'] if pattern)
            self.warning(deprecation_message.format(old='excluded_disks', new='device_blacklist'))

        if 'excluded_disk_re' in instance:
            device_blacklist_extras.append(instance['excluded_disk_re'])
            self.warning(deprecation_message.format(old='excluded_disk_re', new='device_blacklist'))

        if 'excluded_mountpoint_re' in instance:
            mount_point_blacklist_extras.append(instance['excluded_mountpoint_re'])
            self.warning(deprecation_message.format(old='excluded_mountpoint_re', new='mount_point_blacklist'))

        # Any without valid patterns will become None
        self._file_system_whitelist = self._compile_valid_patterns(self._file_system_whitelist, casing=re.I)
        self._file_system_blacklist = self._compile_valid_patterns(
            self._file_system_blacklist, casing=re.I, extra_patterns=file_system_blacklist_extras
        )
        self._device_whitelist = self._compile_valid_patterns(self._device_whitelist)
        self._device_blacklist = self._compile_valid_patterns(
            self._device_blacklist, extra_patterns=device_blacklist_extras
        )
        self._mount_point_whitelist = self._compile_valid_patterns(self._mount_point_whitelist)
        self._mount_point_blacklist = self._compile_valid_patterns(
            self._mount_point_blacklist, extra_patterns=mount_point_blacklist_extras
        )

    def _compile_valid_patterns(self, patterns, casing=IGNORE_CASE, extra_patterns=None):
        valid_patterns = []

        if isinstance(patterns, string_types):
            patterns = [patterns]
        else:
            patterns = list(patterns)

        if extra_patterns:
            for extra_pattern in extra_patterns:
                if extra_pattern not in patterns:
                    patterns.append(extra_pattern)

        for pattern in patterns:
            # Ignore empty patterns as they match everything
            if not pattern:
                continue

            try:
                re.compile(pattern, casing)
            except Exception:
                self.log.warning('{} is not a valid regular expression and will be ignored'.format(pattern))
            else:
                valid_patterns.append(pattern)

        if valid_patterns:
            return re.compile('|'.join(valid_patterns), casing)

    def _compile_tag_re(self):
        """
        Compile regex strings from device_tag_re option and return list of compiled regex/tag pairs
        """
        device_tag_list = []
        for regex_str, tags in iteritems(self._device_tag_re):
            try:
                device_tag_list.append([re.compile(regex_str, IGNORE_CASE), [t.strip() for t in tags.split(',')]])
            except TypeError:
                self.log.warning('{} is not a valid regular expression and will be ignored'.format(regex_str))
        self._device_tag_re = device_tag_list
