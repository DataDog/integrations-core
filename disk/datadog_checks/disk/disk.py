# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import platform
import re
import xml.etree.ElementTree as ET

import psutil
from six import iteritems, string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output
from datadog_checks.base.utils.timeout import TimeoutException, timeout

# See: https://github.com/DataDog/integrations-core/pull/1109#discussion_r167133580
IGNORE_CASE = re.I if platform.system() == 'Windows' else 0


class Disk(AgentCheck):
    """ Collects metrics about the machine's disks. """

    METRIC_DISK = 'system.disk.{}'
    METRIC_INODE = 'system.fs.inodes.{}'

    def __init__(self, name, init_config, instances):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Disk check only supports one configured instance.')
        super(Disk, self).__init__(name, init_config, instances)

        instance = instances[0]
        self._use_mount = is_affirmative(instance.get('use_mount', False))
        self._all_partitions = is_affirmative(instance.get('all_partitions', False))
        self._file_system_whitelist = instance.get('file_system_whitelist', [])
        self._file_system_blacklist = instance.get('file_system_blacklist', [])
        self._device_whitelist = instance.get('device_whitelist', [])
        self._device_blacklist = instance.get('device_blacklist', [])
        self._mount_point_whitelist = instance.get('mount_point_whitelist', [])
        self._mount_point_blacklist = instance.get('mount_point_blacklist', [])
        self._tag_by_filesystem = is_affirmative(instance.get('tag_by_filesystem', False))
        self._tag_by_label = is_affirmative(instance.get('tag_by_label', True))
        self._device_tag_re = instance.get('device_tag_re', {})
        self._custom_tags = instance.get('tags', [])
        self._service_check_rw = is_affirmative(instance.get('service_check_rw', False))
        self._min_disk_size = instance.get('min_disk_size', 0) * 1024 * 1024
        self._blkid_cache_file = instance.get('blkid_cache_file')

        self._compile_pattern_filters(instance)
        self._compile_tag_re()
        self._blkid_label_re = re.compile('LABEL=\"(.*?)\"', re.I)

        self.devices_label = {}

    def check(self, instance):
        """Get disk space/inode stats"""
        if self._tag_by_label and Platform.is_linux():
            self.devices_label = self._get_devices_label()

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

            # Exclude disks with size less than min_disk_size
            if disk_usage.total <= self._min_disk_size:
                if disk_usage.total > 0:
                    self.log.info('Excluding device %s with total disk size %s', part.device, disk_usage.total)
                continue

            # For later, latency metrics
            self._valid_disks[part.device] = (part.fstype, part.mountpoint)
            self.log.debug('Passed: %s', part.device)

            device_name = part.mountpoint if self._use_mount else part.device

            tags = [part.fstype, 'filesystem:{}'.format(part.fstype)] if self._tag_by_filesystem else []
            tags.extend(self._custom_tags)

            # apply device/mountpoint specific tags
            for regex, device_tags in self._device_tag_re:
                if regex.match(device_name):
                    tags.extend(device_tags)

            if self.devices_label.get(device_name):
                tags.append(self.devices_label.get(device_name))

            # legacy check names c: vs psutil name C:\\
            if Platform.is_win32():
                device_name = device_name.strip('\\').lower()

            tags.append('device:{}'.format(device_name))
            tags.append('device_name:{}'.format(os.path.basename(part.device)))
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
        self.log.debug('_exclude_disk: %s, %s, %s', device, file_system, mount_point)

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
            self.log.debug('IO Counters: %s -> %s', disk_name, disk)
            try:
                # x100 to have it as a percentage,
                # /1000 as psutil returns the value in ms
                read_time_pct = disk.read_time * 100 / 1000
                write_time_pct = disk.write_time * 100 / 1000
                metric_tags = [] if self._custom_tags is None else self._custom_tags[:]
                metric_tags.append('device:{}'.format(disk_name))
                metric_tags.append('device_name:{}'.format(os.path.basename(disk_name)))
                if self.devices_label.get(disk_name):
                    metric_tags.append(self.devices_label.get(disk_name))
                self.rate(self.METRIC_DISK.format('read_time_pct'), read_time_pct, tags=metric_tags)
                self.rate(self.METRIC_DISK.format('write_time_pct'), write_time_pct, tags=metric_tags)
            except AttributeError as e:
                # Some OS don't return read_time/write_time fields
                # http://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
                self.log.debug('Latency metrics not collected for %s: %s', disk_name, e)

    def _compile_pattern_filters(self, instance):
        # Force exclusion of CDROM (iso9660)
        file_system_blacklist_extras = ['iso9660$']
        device_blacklist_extras = []
        mount_point_blacklist_extras = []

        deprecation_message = '`%s` is deprecated and will be removed in 6.9. Please use `%s` instead.'

        if 'excluded_filesystems' in instance:
            file_system_blacklist_extras.extend(
                '{}$'.format(pattern) for pattern in instance['excluded_filesystems'] if pattern
            )
            self.warning(deprecation_message, 'excluded_filesystems', 'file_system_blacklist')

        if 'excluded_disks' in instance:
            device_blacklist_extras.extend('{}$'.format(pattern) for pattern in instance['excluded_disks'] if pattern)
            self.warning(deprecation_message, 'excluded_disks', 'device_blacklist')

        if 'excluded_disk_re' in instance:
            device_blacklist_extras.append(instance['excluded_disk_re'])
            self.warning(deprecation_message, 'excluded_disk_re', 'device_blacklist')

        if 'excluded_mountpoint_re' in instance:
            mount_point_blacklist_extras.append(instance['excluded_mountpoint_re'])
            self.warning(deprecation_message, 'excluded_mountpoint_re', 'mount_point_blacklist')

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
                self.log.warning('%s is not a valid regular expression and will be ignored', pattern)
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
                self.log.warning('%s is not a valid regular expression and will be ignored', regex_str)
        self._device_tag_re = device_tag_list

    def _get_devices_label(self):
        """
        Get every label to create tags and returns a map of device name to label:value
        """
        if not self._blkid_cache_file:
            return self._get_devices_label_from_blkid()
        return self._get_devices_label_from_blkid_cache()

    def _get_devices_label_from_blkid(self):
        devices_label = {}
        try:
            blkid_out, _, _ = get_subprocess_output(['blkid'], self.log)
            all_devices = [l.split(':', 1) for l in blkid_out.splitlines()]

            for d in all_devices:
                # Line sample
                # /dev/sda1: LABEL="MYLABEL" UUID="5eea373d-db36-4ce2-8c71-12ce544e8559" TYPE="ext4"
                labels = self._blkid_label_re.findall(d[1])
                if labels:
                    devices_label[d[0]] = 'label:{}'.format(labels[0])

        except SubprocessOutputEmptyError:
            self.log.debug("Couldn't use blkid to have device labels")

        return devices_label

    def _get_devices_label_from_blkid_cache(self):
        devices_label = {}
        try:
            with open(self._blkid_cache_file, 'r') as blkid_cache_file_handler:
                blkid_cache_data = blkid_cache_file_handler.readlines()
        except IOError as e:
            self.log.warning("Couldn't read the blkid cache file %s: %s", self._blkid_cache_file, e)
            return devices_label

        # Line sample
        # <device DEVNO="0x0801" LABEL="MYLABEL" UUID="..." TYPE="ext4">/dev/sda1</device>
        for line in blkid_cache_data:
            try:
                root = ET.fromstring(line)
                device = root.text
                label = root.attrib.get('LABEL')
                if label and device:
                    devices_label[device] = 'label:{}'.format(label)
            except ET.ParseError as e:
                self.log.warning(
                    'Failed to parse line %s because of %s - skipping the line (some labels might be missing)', line, e
                )

        return devices_label
