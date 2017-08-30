# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib

# 3rd party

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output

EVENT_TYPE = SOURCE_TYPE_NAME = 'nfsstat'


class NfsstatCheck(AgentCheck):

    def check(self, instance):
        # get the mounts, to get some additional metadata for tags
        with open("/proc/mounts") as f:
            mounts_raw = f.readlines()

        all_mounts = [l.strip().split() for l in mounts_raw]

        # get the stats from nfsiostat-sysstat
        stat_out, _, _ = get_subprocess_output("nfsiostat-sysstat", self.log)
        all_devices = [l.strip().split() for l in stat_out.splitlines()]
        devices_raw = [l for l in all_devices[1:] if l]
        devices = []

        for d in devices_raw:
            if d[0] == "Filesystem:":
                continue
            device = Device(d)
            device.set_mount(all_mounts)
            devices.append(device)

        for device in devices:
            self.gauge('nfsstat.blocks_read_per_sec', device.blocks_read, tags=device.tags)
            self.gauge('nfsstat.blocks_written_per_sec', device.blocks_written, tags=device.tags)
            self.gauge('nfsstat.blocks_read_direct_per_sec', device.blocks_read_direct, tags=device.tags)
            self.gauge('nfsstat.blocks_written_direct_per_sec', device.blocks_written_direct, tags=device.tags)
            self.gauge('nfsstat.blocks_read_from_server_per_sec', device.blocks_read_from_server, tags=device.tags)
            self.gauge('nfsstat.blocks_written_to_server_per_sec', device.blocks_written_to_server, tags=device.tags)
            self.gauge('nfsstat.ops_per_sec', device.ops, tags=device.tags)
            self.gauge('nfsstat.read_ops_per_sec', device.read_ops, tags=device.tags)
            self.gauge('nfsstat.write_ops_per_sec', device.write_ops, tags=device.tags)


class Device(object):
    def __init__(self, device):
        self.device_name = device[0]
        self.blocks_read = device[1]
        self.blocks_written = device[2]
        self.blocks_read_direct = device[3]
        self.blocks_written_direct = device[4]
        self.blocks_read_from_server = device[5]
        self.blocks_written_to_server = device[6]
        self.ops = device[7]
        self.read_ops = device[8]
        self.write_ops = device[9]

        self.nfs_server = self.device_name.split(":")[0]
        self.nfs_export = self.device_name.split(":")[1]

        self.tags = []
        self.tags.append("nfs_server:{0}".format(self.nfs_server))
        self.tags.append("nfs_export:{0}".format(self.nfs_export))

    def set_mount(self, mounts):
        for m in mounts:
            if m[0] == self.device_name:
                self.mount = m[0]
                self.tags.append("nfs_mount:{0}".format(self.mount))
                break
