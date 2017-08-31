# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# 3rd party

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output

EVENT_TYPE = SOURCE_TYPE_NAME = 'nfsstat'

class NfsStatCheck(AgentCheck):

    metric_prefix = 'system.nfs.'

    def check(self, instance):
        # get the stats from nfsiostat-sysstat
        stat_out, _, _ = get_subprocess_output("nfsiostat-sysstat", self.log)
        all_devices = [l.strip().split() for l in stat_out.splitlines()]
        devices_raw = [l for l in all_devices[1:] if l]

        all_mounts = self.get_mounts()

        devices = []
        metadata = []
        for d in devices_raw:
            if d[0] == "Filesystem:":
                # if the first element is the metadata,
                # set it as the metadata and continue
                metadata = d
                continue
            device = Device(d, metadata, all_mounts, self.log)
            devices.append(device)

        for device in devices:
            self.gauge(self.metric_prefix + 'read_per_sec',
                        device.read, tags=device.tags)
            self.gauge(self.metric_prefix + 'writes_per_sec',
                        device.writes, tags=device.tags)
            self.gauge(self.metric_prefix + 'read_direct_per_sec',
                        device.read_direct, tags=device.tags)
            self.gauge(self.metric_prefix + 'writes_direct_per_sec',
                        device.writes_direct, tags=device.tags)
            self.gauge(self.metric_prefix + 'read_from_server_per_sec',
                        device.read_from_server, tags=device.tags)
            self.gauge(self.metric_prefix + 'written_to_server_per_sec',
                        device.written_to_server, tags=device.tags)
            self.gauge(self.metric_prefix + 'ops_per_sec',
                        device.ops, tags=device.tags)
            self.gauge(self.metric_prefix + 'read_ops_per_sec',
                        device.read_ops, tags=device.tags)
            self.gauge(self.metric_prefix + 'write_ops_per_sec',
                        device.write_ops, tags=device.tags)

    def get_mounts(self):
        mounts_raw = self.read_mounts()
        all_mounts = [l.strip().split() for l in mounts_raw]
        return all_mounts

    def read_mounts(self):
        # get the mounts, to get some additional metadata for tags
        with open("/proc/mounts") as f:
            mounts_raw = f.readlines()
        return mounts_raw


# Each NFS device is different
# but it all requires essentially the same processing
# Making each device an object class makes the
# processing of the data a bit more straightforward
class Device(object):
    attrs = ['',
            'read',
            'writes',
            'read_direct',
            'writes_direct',
            'read_from_server',
            'written_to_server']

    def __init__(self, device, metadata, all_mounts, log):
        self.log = log

        self._device_data = device
        self._metadata = metadata
        self.device_name = device[0]
        self.ops = float(device[7])
        self.read_ops = float(device[8])
        self.write_ops = float(device[9])
        self.nfs_server = self.device_name.split(":")[0]
        self.nfs_export = self.device_name.split(":")[1]

        # all mounts are not related to the device, only the one it is mounted on
        self._set_mount(all_mounts)
        self._parse_data()
        self._parse_tags()


    def _parse_data(self):
        for i, m in enumerate(self._metadata):
            if i == 0:
                continue
            if i > 6:
                break

            # Blk, kB and MB are the possible options for how these are
            # displayed as detailed in the man page.
            # The rates are displayed either as blocks, kilobytes, or megabytes
            if m.find("Blk") >= 0:
                dat = self._convert_blk(self._device_data[i])
                setattr(self, self.attrs[i], dat)
            elif m.find("kB") >= 0:
                dat = self._convert_kB(self._device_data[i])
                setattr(self, self.attrs[i], dat)
            elif m.find("MB") >= 0:
                dat = self._convert_MB(self._device_data[i])
                setattr(self, self.attrs[i], dat)

    def _convert_blk(self, number):
        # a block is either 1K bytes or,
        # if the environment variable POSIXLY_CORRECT is set, 512 bytes
        convert = float(1000)
        if os.getenv('POSIXLY_CORRECT', False):
            convert = float(512)
        return float(number) * convert

    def _convert_kB(self, number):
        return float(number) * float(1024)

    def _convert_MB(self, number):
        return float(number) * float(1048576)

    def _parse_tags(self):
        self.tags = []
        self.tags.append("nfs_server:{0}".format(self.nfs_server))
        self.tags.append("nfs_export:{0}".format(self.nfs_export))
        self.tags.append("nfs_mount:{0}".format(self.mount))

    def _set_mount(self, mounts):
        # for now, only the mount point is relevant
        for m in mounts:
            if m[0] == self.device_name:
                self.mount = m[1]
                break
