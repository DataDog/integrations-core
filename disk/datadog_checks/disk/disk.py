# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import platform
import re

from six import iteritems
try:
    import psutil
except ImportError:
    psutil = None

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import get_subprocess_output
from datadog_checks.base.utils.timeout import timeout, TimeoutException

IGNORE_CASE = re.I if platform.system() == 'Windows' else 0


class Disk(AgentCheck):
    """ Collects metrics about the machine's disks. """
    # -T for filesystem info
    DF_COMMAND = ['df', '-T']
    METRIC_DISK = 'system.disk.{}'
    METRIC_INODE = 'system.fs.inodes.{}'

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Disk check only supports one configured instance.')
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)

        # Get the configuration once for all
        self._load_conf(instances[0])
        self._compile_tag_re()

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

    def _load_conf(self, instance):
        self._use_mount = is_affirmative(instance.get('use_mount', False))
        self._excluded_filesystems = instance.get('excluded_filesystems', [])
        self._excluded_disks = instance.get('excluded_disks', [])
        self._excluded_disk_re = re.compile(instance.get('excluded_disk_re', '^$'))
        self._excluded_mountpoint_re = re.compile(instance.get('excluded_mountpoint_re', '^$'))
        self._tag_by_filesystem = is_affirmative(instance.get('tag_by_filesystem', False))
        self._all_partitions = is_affirmative(instance.get('all_partitions', False))
        self._device_tag_re = instance.get('device_tag_re', {})
        self._custom_tags = instance.get('tags', [])
        self._service_check_rw = is_affirmative(instance.get('service_check_rw', False))

        # Force exclusion of CDROM (iso9660) from disk check
        self._excluded_filesystems.append('iso9660')

    def collect_metrics_psutil(self):
        self._valid_disks = {}
        for part in psutil.disk_partitions(all=True):
            # we check all exclude conditions
            if self._exclude_disk_psutil(part):
                continue

            # Get disk metrics here to be able to exclude on total usage
            try:
                disk_usage = timeout(5)(psutil.disk_usage)(part.mountpoint)
            except TimeoutException:
                self.log.warning(
                    u'Timeout while retrieving the disk usage of `%s` mountpoint. Skipping...',
                    part.mountpoint
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

            for metric_name, metric_value in iteritems(self._collect_part_metrics(part, disk_usage)):
                self.gauge(metric_name, metric_value, tags=tags, device_name=device_name)

            # Add in a disk read write or read only check
            if self._service_check_rw:
                rwro = {'rw', 'ro'} & set(part.opts.split(','))
                if len(rwro) == 1:
                    self.service_check(
                        'disk.read_write',
                        AgentCheck.OK if rwro.pop() == 'rw' else AgentCheck.CRITICAL,
                        tags=tags + ['device:{}'.format(device_name)]
                    )
                else:
                    self.service_check(
                        'disk.read_write', AgentCheck.UNKNOWN,
                        tags=tags + ['device:{}'.format(device_name)]
                    )

        self.collect_latency_metrics()

    def _exclude_disk_psutil(self, part):
        # skip cd-rom drives with no disk in it; they may raise
        # ENOENT, pop-up a Windows GUI error for a non-ready
        # partition or just hang;
        # and all the other excluded disks
        skip_win = Platform.is_win32() and ('cdrom' in part.opts or part.fstype == '')
        return skip_win or self._exclude_disk(part.device, part.fstype, part.mountpoint)

    def _exclude_disk(self, name, filesystem, mountpoint):
        """
        Return True for disks we don't want or that match regex in the config file
        """
        self.log.debug('_exclude_disk: {}, {}, {}'.format(name, filesystem, mountpoint))

        # Hack for NFS secure mounts
        # Secure mounts might look like this: '/mypath (deleted)', we should
        # ignore all the bits not part of the mountpoint name. Take also into
        # account a space might be in the mountpoint.
        mountpoint = mountpoint.rsplit(' ', 1)[0]

        name_empty = not name or name == 'none'

        # allow empty names if `all_partitions` is `true` so we can evaluate mountpoints
        if name_empty and not self._all_partitions:
            return True
        # device is listed in `excluded_disks`
        elif not name_empty and name in self._excluded_disks:
            return True
        # device name matches `excluded_disk_re`
        elif not name_empty and self._excluded_disk_re.match(name):
            return True
        # device mountpoint matches `excluded_mountpoint_re`
        elif self._excluded_mountpoint_re.match(mountpoint):
            return True
        # fs is listed in `excluded_filesystems`
        elif filesystem in self._excluded_filesystems:
            return True
        # all good, don't exclude the disk
        else:
            return False

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
            self.log.warning(
                u'Timeout while retrieving the disk usage of `%s` mountpoint. Skipping...',
                mountpoint
            )
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
                self.rate(self.METRIC_DISK.format('read_time_pct'),
                          read_time_pct, device_name=disk_name, tags=self._custom_tags)
                self.rate(self.METRIC_DISK.format('write_time_pct'),
                          write_time_pct, device_name=disk_name, tags=self._custom_tags)
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

            for metric_name, value in iteritems(self._collect_metrics_manually(device)):
                self.gauge(metric_name, value, tags=tags, device_name=device_name)

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
            device and len(device) > 1
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

    def _compile_tag_re(self):
        """
        Compile regex strings from device_tag_re option and return list of compiled regex/tag pairs
        """
        device_tag_list = []
        for regex_str, tags in iteritems(self._device_tag_re):
            try:
                device_tag_list.append([
                    re.compile(regex_str, IGNORE_CASE),
                    [t.strip() for t in tags.split(',')]
                ])
            except TypeError:
                self.log.warning('{} is not a valid regular expression and will be ignored'.format(regex_str))
        self._device_tag_re = device_tag_list
