# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import array
from collections import defaultdict
import fcntl
import itertools
import os
import struct

# 3rd party
import psutil

# project
from datadog_checks.checks import AgentCheck

MIXED = "mixed"
DATA = "data"
METADATA = "metadata"
SYSTEM = "system"
SINGLE = "single"
RAID0 = "raid0"
RAID1 = "raid1"
RAID5 = "raid5"
RAID6 = "raid6"
RAID10 = "raid10"
DUP = "dup"
UNKNOWN = "unknown"
GLB_RSV = "globalreserve"

# https://github.com/torvalds/linux/blob/98820a7e244b17b8a4d9e9d1ff9d3b4e5bfca58b/include/uapi/linux/btrfs_tree.h#L829-L840
# https://github.com/torvalds/linux/blob/98820a7e244b17b8a4d9e9d1ff9d3b4e5bfca58b/include/uapi/linux/btrfs_tree.h#L879
FLAGS_MAPPER = defaultdict(lambda: (SINGLE, UNKNOWN), {
    1: (SINGLE, DATA),
    2: (SINGLE, SYSTEM),
    4: (SINGLE, METADATA),
    5: (SINGLE, MIXED),
    9: (RAID0, DATA),
    10: (RAID0, SYSTEM),
    12: (RAID0, METADATA),
    13: (RAID0, MIXED),
    17: (RAID1, DATA),
    18: (RAID1, SYSTEM),
    20: (RAID1, METADATA),
    21: (RAID1, MIXED),
    33: (DUP, DATA),
    34: (DUP, SYSTEM),
    36: (DUP, METADATA),
    37: (DUP, MIXED),
    65: (RAID10, DATA),
    66: (RAID10, SYSTEM),
    68: (RAID10, METADATA),
    69: (RAID10, MIXED),
    129: (RAID5, DATA),
    130: (RAID5, SYSTEM),
    132: (RAID5, METADATA),
    133: (RAID5, MIXED),
    257: (RAID6, DATA),
    258: (RAID6, SYSTEM),
    260: (RAID6, METADATA),
    261: (RAID6, MIXED),
    562949953421312: (SINGLE, GLB_RSV)
})

BTRFS_IOC_SPACE_INFO = 0xc0109414
BTRFS_IOC_DEV_INFO = 0xd000941e
BTRFS_IOC_FS_INFO = 0x8400941f

TWO_LONGS_STRUCT = struct.Struct("=2Q")  # 2 Longs
THREE_LONGS_STRUCT = struct.Struct("=3Q")  # 3 Longs

# https://github.com/thorvalds/linux/blob/master/include/uapi/linux/btrfs.h#L173
# https://github.com/thorvalds/linux/blob/master/include/uapi/linux/btrfs.h#L182
BTRFS_DEV_INFO_STRUCT = struct.Struct("=Q16B381Q1024B")
BTRFS_FS_INFO_STRUCT = struct.Struct("=2Q16B4I122Q")


def sized_array(count):
    return array.array("B", itertools.repeat(0, count))


class FileDescriptor(object):

    def __init__(self, mountpoint):
        self.fd = os.open(mountpoint, os.O_DIRECTORY)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.fd)

    def fileno(self):
        return self.fd

    def open(self, dir):
        return self.fd


class BTRFS(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("BTRFS check only supports one configured instance.")

    def get_usage(self, mountpoint):
        results = []

        with FileDescriptor(mountpoint) as fd:

            # Get the struct size needed
            # https://github.com/spotify/linux/blob/master/fs/btrfs/ioctl.h#L46-L50
            ret = sized_array(TWO_LONGS_STRUCT.size)
            fcntl.ioctl(fd, BTRFS_IOC_SPACE_INFO, ret)
            _, total_spaces = TWO_LONGS_STRUCT.unpack(ret)

            # Allocate it
            buffer_size = TWO_LONGS_STRUCT.size + total_spaces * THREE_LONGS_STRUCT.size

            data = sized_array(buffer_size)
            TWO_LONGS_STRUCT.pack_into(data, 0, total_spaces, 0)
            fcntl.ioctl(fd, BTRFS_IOC_SPACE_INFO, data)

        _, total_spaces = TWO_LONGS_STRUCT.unpack_from(ret, 0)
        for offset in xrange(TWO_LONGS_STRUCT.size, buffer_size, THREE_LONGS_STRUCT.size):
            # https://github.com/spotify/linux/blob/master/fs/btrfs/ioctl.h#L40-L44
            flags, total_bytes, used_bytes = THREE_LONGS_STRUCT.unpack_from(data, offset)
            results.append((flags, total_bytes, used_bytes))

        return results

    def get_unallocated_space(self, mountpoint):
        unallocated_bytes = 0

        with FileDescriptor(mountpoint) as fd:

            # Retrieve the fs info to get the number of devices and max device id
            fs_info = sized_array(BTRFS_FS_INFO_STRUCT.size)
            fcntl.ioctl(fd, BTRFS_IOC_FS_INFO, fs_info)
            fs_info = BTRFS_FS_INFO_STRUCT.unpack_from(fs_info, 0)
            max_id, num_devices = fs_info[0], fs_info[1]

            # Loop through all devices, and sum the number of unallocated bytes on each one
            for dev_id in xrange(max_id + 1):
                if num_devices == 0:
                    break
                try:
                    dev_info = sized_array(BTRFS_DEV_INFO_STRUCT.size)
                    BTRFS_DEV_INFO_STRUCT.pack_into(dev_info, 0, dev_id, *([0] * 1421))
                    fcntl.ioctl(fd, BTRFS_IOC_DEV_INFO, dev_info)
                    dev_info = BTRFS_DEV_INFO_STRUCT.unpack_from(dev_info, 0)

                    unallocated_bytes = unallocated_bytes + dev_info[18] - dev_info[17]
                    num_devices = num_devices - 1

                except IOError as e:
                    self.log.debug("Cannot get device info for device id %s: %s", dev_id, e)

            if num_devices != 0:
                # Could not retrieve the info for all the devices, skip the metric
                return None
        return unallocated_bytes

    def check(self, instance):
        btrfs_devices = {}
        excluded_devices = instance.get('excluded_devices', [])
        custom_tags = instance.get('tags', [])

        for p in psutil.disk_partitions():
            if p.fstype == 'btrfs' and p.device not in btrfs_devices and p.device not in excluded_devices:
                btrfs_devices[p.device] = p.mountpoint

        if len(btrfs_devices) == 0:
            raise Exception("No btrfs device found")

        for device, mountpoint in btrfs_devices.iteritems():
            for flags, total_bytes, used_bytes in self.get_usage(mountpoint):
                replication_type, usage_type = FLAGS_MAPPER[flags]
                tags = [
                    'usage_type:{}'.format(usage_type),
                    'replication_type:{}'.format(replication_type),
                    "device:{}".format(device)
                ]
                tags.extend(custom_tags)

                free = total_bytes - used_bytes
                usage = float(used_bytes) / float(total_bytes)

                self.gauge('system.disk.btrfs.total', total_bytes, tags=tags)
                self.gauge('system.disk.btrfs.used', used_bytes, tags=tags)
                self.gauge('system.disk.btrfs.free', free, tags=tags)
                self.gauge('system.disk.btrfs.usage', usage, tags=tags)

            unallocated_bytes = self.get_unallocated_space(mountpoint)
            if unallocated_bytes is not None:
                tags = ["device:{}".format(device)] + custom_tags
                self.gauge("system.disk.btrfs.unallocated", unallocated_bytes, tags=tags)
            else:
                self.log.debug(
                    "Could not retrieve the number of unallocated bytes for all devices,"
                    " skipping metric for mountpoint {}".format(mountpoint)
                )
