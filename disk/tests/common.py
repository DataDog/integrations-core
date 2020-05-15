# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.utils import ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))

if ON_WINDOWS:
    DEFAULT_DEVICE_NAME = 'c:'
    DEFAULT_DEVICE_BASE_NAME = 'c:'
    DEFAULT_FILE_SYSTEM = 'ntfs'
    DEFAULT_MOUNT_POINT = 'c:'
else:
    DEFAULT_DEVICE_NAME = '/dev/sda1'
    DEFAULT_DEVICE_BASE_NAME = 'sda1'
    DEFAULT_FILE_SYSTEM = 'ext4'
    DEFAULT_MOUNT_POINT = '/'

EXPECTED_METRICS = [
    {"metric": "system.disk.free", "device": "/dev/vda1"},
    {"metric": "system.disk.free", "device": "overlay"},
    {"metric": "system.disk.free", "device": "shm"},
    {"metric": "system.disk.free", "device": "tmpfs"},
    {"metric": "system.disk.in_use", "device": "/dev/vda1"},
    {"metric": "system.disk.in_use", "device": "overlay"},
    {"metric": "system.disk.in_use", "device": "shm"},
    {"metric": "system.disk.in_use", "device": "tmpfs"},
    {"metric": "system.disk.total", "device": "/dev/vda1"},
    {"metric": "system.disk.total", "device": "overlay"},
    {"metric": "system.disk.total", "device": "shm"},
    {"metric": "system.disk.total", "device": "tmpfs"},
    {"metric": "system.disk.used", "device": "/dev/vda1"},
    {"metric": "system.disk.used", "device": "overlay"},
    {"metric": "system.disk.used", "device": "shm"},
    {"metric": "system.disk.used", "device": "tmpfs"},
    {"metric": "system.fs.inodes.free", "device": "/dev/vda1"},
    {"metric": "system.fs.inodes.free", "device": "overlay"},
    {"metric": "system.fs.inodes.free", "device": "shm"},
    {"metric": "system.fs.inodes.free", "device": "tmpfs"},
    {"metric": "system.fs.inodes.in_use", "device": "/dev/vda1"},
    {"metric": "system.fs.inodes.in_use", "device": "overlay"},
    {"metric": "system.fs.inodes.in_use", "device": "shm"},
    {"metric": "system.fs.inodes.in_use", "device": "tmpfs"},
    {"metric": "system.fs.inodes.total", "device": "/dev/vda1"},
    {"metric": "system.fs.inodes.total", "device": "overlay"},
    {"metric": "system.fs.inodes.total", "device": "shm"},
    {"metric": "system.fs.inodes.total", "device": "tmpfs"},
    {"metric": "system.fs.inodes.used", "device": "/dev/vda1"},
    {"metric": "system.fs.inodes.used", "device": "overlay"},
    {"metric": "system.fs.inodes.used", "device": "shm"},
    {"metric": "system.fs.inodes.used", "device": "tmpfs"},
]
