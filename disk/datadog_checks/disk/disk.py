# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import platform
import re
from xml.etree import ElementTree as ET

import psutil
from six import iteritems, string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output
from datadog_checks.base.utils.timeout import TimeoutException, timeout

if platform.system() == 'Windows':
    import win32wnet

    # See: https://github.com/DataDog/integrations-core/pull/1109#discussion_r167133580
    IGNORE_CASE = re.I

    def _base_device_name(device):
        return device.strip('\\').lower()

else:
    IGNORE_CASE = 0

    def _base_device_name(device):
        return os.path.basename(device)


class Disk(AgentCheck):
    """Collects metrics about the machine's disks."""

    METRIC_DISK = 'system.disk.{}'
    METRIC_INODE = 'system.fs.inodes.{}'

    def __init__(self, name, init_config, instances):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Disk check only supports one configured instance.')
        super(Disk, self).__init__(name, init_config, instances)

        instance = instances[0]
        self._use_mount = is_affirmative(instance.get('use_mount', False))
        self._all_partitions = is_affirmative(instance.get('all_partitions', False))
        self._file_system_include = instance.get('file_system_include', []) or instance.get('file_system_whitelist', [])
        self._file_system_exclude = instance.get('file_system_exclude', []) or instance.get('file_system_blacklist', [])
        # FIXME (8.X): Exclude special file systems by default
        self._include_all_devices = is_affirmative(instance.get('include_all_devices', True))
        self._device_include = instance.get('device_include', []) or instance.get('device_whitelist', [])
        self._device_exclude = instance.get('device_exclude', []) or instance.get('device_blacklist', [])
        self._mount_point_include = instance.get('mount_point_include', []) or instance.get('mount_point_whitelist', [])
        self._mount_point_exclude = instance.get('mount_point_exclude', []) or instance.get('mount_point_blacklist', [])
        self._tag_by_filesystem = is_affirmative(instance.get('tag_by_filesystem', False))
        self._tag_by_label = is_affirmative(instance.get('tag_by_label', True))
        self._device_tag_re = instance.get('device_tag_re', {})
        self._custom_tags = instance.get('tags', [])
        self._service_check_rw = is_affirmative(instance.get('service_check_rw', False))
        self._min_disk_size = instance.get('min_disk_size', 0) * 1024 * 1024
        self._blkid_cache_file = instance.get('blkid_cache_file')
        self._use_lsblk = is_affirmative(instance.get('use_lsblk', False))
        self._timeout = instance.get('timeout', 5)
        self._compile_pattern_filters(instance)
        self._compile_tag_re()
        self._blkid_label_re = re.compile('LABEL=\"(.*?)\"', re.I)

        if self._use_lsblk and self._blkid_cache_file:
            raise ConfigurationError("Only one of 'use_lsblk' and 'blkid_cache_file' can be set at the same time.")

        if platform.system() == 'Windows':
            self._manual_mounts = instance.get('create_mounts', [])
            self._create_manual_mounts()

        deprecations_init_conf = {
            'file_system_global_blacklist': 'file_system_global_exclude',
            'device_global_blacklist': 'device_global_exclude',
            'mount_point_global_blacklist': 'mount_point_global_exclude',
        }
        for old_name, new_name in deprecations_init_conf.items():
            if init_config.get(old_name):
                self.warning(
                    '`%s` is deprecated and will be removed in a future release. Please use `%s` instead.',
                    old_name,
                    new_name,
                )

        deprecations_instance = {
            'file_system_whitelist': 'file_system_include',
            'file_system_blacklist': 'file_system_exclude',
            'device_whitelist': 'device_include',
            'device_blacklist': 'device_exclude',
            'mount_point_whitelist': 'mount_point_include',
            'mount_point_blacklist': 'mount_point_exclude',
            'excluded_filesystems': 'file_system_exclude',
            'excluded_disks': 'device_exclude',
            'excluded_disk_re': 'device_exclude',
            'excluded_mountpoint_re': 'mount_point_exclude',
        }
        for old_name, new_name in deprecations_instance.items():
            if instance.get(old_name):
                self.warning(
                    '`%s` is deprecated and will be removed in a future release. Please use `%s` instead.',
                    old_name,
                    new_name,
                )

        self.devices_label = {}

    def check(self, _):
        """Get disk space/inode stats"""
        if self._tag_by_label and Platform.is_linux():
            self.devices_label = self._get_devices_label()

        for part in psutil.disk_partitions(all=self._include_all_devices):
            # we check all exclude conditions
            if self.exclude_disk(part):
                self.log.debug('Excluding device %s', part.device)
                continue

            # Get disk metrics here to be able to exclude on total usage
            try:
                disk_usage = timeout(self._timeout)(psutil.disk_usage)(part.mountpoint)
            except TimeoutException:
                self.log.warning(
                    u'Timeout after %d seconds while retrieving the disk usage of `%s` mountpoint. '
                    u'You might want to change the timeout length in the settings.',
                    self._timeout,
                    part.mountpoint,
                )
                continue
            except Exception as e:
                self.log.warning(
                    u'Unable to get disk metrics for %s: %s. '
                    u'You can exclude this mountpoint in the settings if it is invalid.',
                    part.mountpoint,
                    e,
                )
                continue

            # Exclude disks with size less than min_disk_size
            if disk_usage.total <= self._min_disk_size:
                if disk_usage.total > 0:
                    self.log.info('Excluding device %s with total disk size %s', part.device, disk_usage.total)
                continue

            self.log.debug('Passed: %s', part.device)

            tags = self._get_tags(part)
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

    def _get_tags(self, part):
        device_name = part.mountpoint if self._use_mount else part.device
        tags = [part.fstype, 'filesystem:{}'.format(part.fstype)] if self._tag_by_filesystem else []
        tags.extend(self._custom_tags)

        # apply device-specific tags
        device_specific_tags = self._get_device_specific_tags(device_name)
        tags.extend(device_specific_tags)

        # apply device labels as tags (from blkid or lsblk).
        # we want to use the real device name and not the device_name (which can be the mountpoint)
        if self.devices_label.get(part.device):
            tags.extend(self.devices_label.get(part.device))

        # legacy check names c: vs psutil name C:\\
        if Platform.is_win32():
            device_name = device_name.strip('\\').lower()

        tags.append('device:{}'.format(device_name))
        tags.append('device_name:{}'.format(_base_device_name(part.device)))
        return tags

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

        return self._partition_excluded(device, file_system, mount_point) or not self._partition_included(
            device, file_system, mount_point
        )

    def _partition_included(self, device, file_system, mount_point):
        return (
            self._file_system_included(file_system)
            and self._device_included(device)
            and self._mount_point_included(mount_point)
        )

    def _partition_excluded(self, device, file_system, mount_point):
        return (
            self._file_system_excluded(file_system)
            or self._device_excluded(device)
            or self._mount_point_excluded(mount_point)
        )

    def _file_system_included(self, file_system):
        if self._file_system_include is None:
            return True

        return not not self._file_system_include.match(file_system)

    def _file_system_excluded(self, file_system):
        if self._file_system_exclude is None:
            return False

        return not not self._file_system_exclude.match(file_system)

    def _device_included(self, device):
        if not device or self._device_include is None:
            return True

        return not not self._device_include.match(device)

    def _device_excluded(self, device):
        if not device or self._device_exclude is None:
            return False

        return not not self._device_exclude.match(device)

    def _mount_point_included(self, mount_point):
        if self._mount_point_include is None:
            return True

        return not not self._mount_point_include.match(mount_point)

    def _mount_point_excluded(self, mount_point):
        if self._mount_point_exclude is None:
            return False

        return not not self._mount_point_exclude.match(mount_point)

    def _collect_part_metrics(self, part, usage):
        metrics = {}

        for name in ['total', 'used', 'free']:
            # For legacy reasons,  the standard unit it kB
            metrics[self.METRIC_DISK.format(name)] = getattr(usage, name) / 1024

        # FIXME: 8.x, use percent, a lot more logical than in_use
        metrics[self.METRIC_DISK.format('in_use')] = usage.percent / 100

        if Platform.is_unix():
            metrics.update(self._collect_inodes_metrics(part.mountpoint))

        return metrics

    def _collect_inodes_metrics(self, mountpoint):
        metrics = {}
        # we need to timeout this, too.
        try:
            inodes = timeout(self._timeout)(os.statvfs)(mountpoint)
        except TimeoutException:
            self.log.warning(
                u'Timeout after %d seconds while retrieving the disk usage of `%s` mountpoint. '
                u'You might want to change the timeout length in the settings.',
                self._timeout,
                mountpoint,
            )
            return metrics
        except Exception as e:
            self.log.warning(
                u'Unable to get disk metrics for %s: %s. '
                u'You can exclude this mountpoint in the settings if it is invalid.',
                mountpoint,
                e,
            )
            return metrics

        if inodes.f_files != 0:
            total = inodes.f_files
            free = inodes.f_ffree

            metrics[self.METRIC_INODE.format('total')] = total
            metrics[self.METRIC_INODE.format('free')] = free
            metrics[self.METRIC_INODE.format('used')] = total - free
            # FIXME: 8.x, use percent, a lot more logical than in_use
            metrics[self.METRIC_INODE.format('in_use')] = (total - free) / total

        return metrics

    def collect_latency_metrics(self):
        for disk_name, disk in iteritems(psutil.disk_io_counters(True)):
            self.log.debug('IO Counters: %s -> %s', disk_name, disk)
            try:
                metric_tags = [] if self._custom_tags is None else self._custom_tags[:]

                device_specific_tags = self._get_device_specific_tags(disk_name)
                metric_tags.extend(device_specific_tags)

                metric_tags.append('device:{}'.format(disk_name))
                metric_tags.append('device_name:{}'.format(_base_device_name(disk_name)))
                if self.devices_label.get(disk_name):
                    metric_tags.extend(self.devices_label.get(disk_name))
                self.monotonic_count(self.METRIC_DISK.format('read_time'), disk.read_time, tags=metric_tags)
                self.monotonic_count(self.METRIC_DISK.format('write_time'), disk.write_time, tags=metric_tags)
                # FIXME: 8.x, metrics kept for backwards compatibility but are incorrect: the value is not a percentage
                # See: https://github.com/DataDog/integrations-core/pull/7323#issuecomment-756427024
                self.rate(self.METRIC_DISK.format('read_time_pct'), disk.read_time * 100 / 1000, tags=metric_tags)
                self.rate(self.METRIC_DISK.format('write_time_pct'), disk.write_time * 100 / 1000, tags=metric_tags)
            except AttributeError as e:
                # Some OS don't return read_time/write_time fields
                # http://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
                self.log.debug('Latency metrics not collected for %s: %s', disk_name, e)

    def _compile_pattern_filters(self, instance):
        file_system_exclude_extras = self.init_config.get(
            'file_system_global_exclude',
            self.init_config.get('file_system_global_blacklist', self.get_default_file_system_exclude()),
        )
        device_exclude_extras = self.init_config.get(
            'device_global_exclude', self.init_config.get('device_global_blacklist', self.get_default_device_exclude())
        )
        mount_point_exclude_extras = self.init_config.get(
            'mount_point_global_exclude',
            self.init_config.get('mount_point_global_blacklist', self.get_default_mount_mount_exclude()),
        )

        if 'excluded_filesystems' in instance:
            file_system_exclude_extras.extend(
                '{}$'.format(pattern) for pattern in instance['excluded_filesystems'] if pattern
            )

        if 'excluded_disks' in instance:
            device_exclude_extras.extend('{}$'.format(pattern) for pattern in instance['excluded_disks'] if pattern)

        if 'excluded_disk_re' in instance:
            device_exclude_extras.append(instance['excluded_disk_re'])

        if 'excluded_mountpoint_re' in instance:
            mount_point_exclude_extras.append(instance['excluded_mountpoint_re'])

        # Any without valid patterns will become None
        self._file_system_include = self._compile_valid_patterns(self._file_system_include, casing=re.I)
        self._file_system_exclude = self._compile_valid_patterns(
            self._file_system_exclude, casing=re.I, extra_patterns=file_system_exclude_extras
        )
        self._device_include = self._compile_valid_patterns(self._device_include)
        self._device_exclude = self._compile_valid_patterns(self._device_exclude, extra_patterns=device_exclude_extras)
        self._mount_point_include = self._compile_valid_patterns(self._mount_point_include)
        self._mount_point_exclude = self._compile_valid_patterns(
            self._mount_point_exclude, extra_patterns=mount_point_exclude_extras
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
        if self._use_lsblk:
            return self._get_devices_label_from_lsblk()
        elif not self._blkid_cache_file:
            return self._get_devices_label_from_blkid()
        return self._get_devices_label_from_blkid_cache()

    def _get_devices_label_from_lsblk(self):
        """
        Get device labels using the `lsblk` command. Returns a map of device name to label:value
        """
        devices_labels = {}
        try:
            # Use raw output mode (space-separated fields encoded in UTF-8).
            # We want to be compatible with lsblk version 2.19 since
            # it is the last version supported by CentOS 6 and SUSE 11.
            lsblk_out, _, _ = get_subprocess_output(["lsblk", "--noheadings", "--raw", "--output=NAME,LABEL"], self.log)

            for line in lsblk_out.splitlines():
                device, _, label = line.partition(' ')
                if label:
                    # Line sample (device "/dev/sda1" with label " MY LABEL")
                    # sda1  MY LABEL
                    devices_labels["/dev/" + device] = ['label:{}'.format(label), 'device_label:{}'.format(label)]

        except SubprocessOutputEmptyError:
            self.log.debug("Couldn't use lsblk to have device labels")

        return devices_labels

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
                    devices_label[d[0]] = ['label:{}'.format(labels[0]), 'device_label:{}'.format(labels[0])]

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
                    devices_label[device] = ['label:{}'.format(label), 'device_label:{}'.format(label)]
            except ET.ParseError as e:
                self.log.warning(
                    'Failed to parse line %s because of %s - skipping the line (some labels might be missing)', line, e
                )

        return devices_label

    def _get_device_specific_tags(self, device_name):
        device_specific_tags = []

        # apply device/mountpoint specific tags
        for regex, device_tags in self._device_tag_re:
            if regex.match(device_name):
                device_specific_tags.extend(device_tags)
        return device_specific_tags

    def _create_manual_mounts(self):
        """
        on Windows, in order to collect statistics on remote (SMB/NFS) drives, the drive must be mounted
        as the agent user in the agent context, otherwise the agent can't 'see' the drive.  If so configured,
        attempt to mount desired drives
        """
        if not self._manual_mounts:
            self.log.debug("No manual mounts")
        else:
            self.log.debug("Attempting to create %d mounts: ", len(self._manual_mounts))
            for manual_mount in self._manual_mounts:
                remote_machine = manual_mount.get('host')
                share = manual_mount.get('share')
                uname = manual_mount.get('user')
                pword = manual_mount.get('password')
                mtype = manual_mount.get('type')
                mountpoint = manual_mount.get('mountpoint')

                nr = win32wnet.NETRESOURCE()
                if not remote_machine or not share:
                    self.log.error("Invalid configuration.  Drive mount requires remote machine and share point")
                    continue

                if mtype and mtype.lower() == "nfs":
                    nr.lpRemoteName = r"{}:{}".format(remote_machine, share)
                    self.log.debug("Attempting NFS mount: %s", nr.lpRemoteName)
                else:
                    nr.lpRemoteName = r"\\{}\{}".format(remote_machine, share).rstrip('\\')
                    self.log.debug("Attempting SMB mount: %s", nr.lpRemoteName)

                nr.dwType = 0
                nr.lpLocalName = mountpoint
                try:
                    win32wnet.WNetAddConnection2(nr, pword, uname, 0)
                    self.log.debug("Successfully mounted %s as %s", mountpoint, nr.lpRemoteName)
                except Exception as e:
                    self.log.error("Failed to mount %s %s", nr.lpRemoteName, str(e))
                    pass

    @staticmethod
    def get_default_file_system_exclude():
        return [
            # CDROM
            'iso9660$',
            # tracefs
            'tracefs$',
        ]

    @staticmethod
    def get_default_device_exclude():
        return []

    @staticmethod
    def get_default_mount_mount_exclude():
        return [
            # https://github.com/DataDog/datadog-agent/issues/1961
            # https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-1049
            '(/host)?/proc/sys/fs/binfmt_misc$'
        ]
