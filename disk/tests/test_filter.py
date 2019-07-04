# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.dev.utils import ON_WINDOWS
from datadog_checks.disk.disk import IGNORE_CASE, Disk

from .mocks import MockPart
from .utils import requires_windows


def test_default_casing():
    if ON_WINDOWS:
        assert IGNORE_CASE == re.I
    else:
        assert IGNORE_CASE == 0


def test_default_mock():
    c = Disk('disk', None, {}, [{}])

    assert c.exclude_disk(MockPart()) is False


def test_bad_config_string_regex():
    instance = {
        'file_system_whitelist': 'test',
        'file_system_blacklist': 'test',
        'device_whitelist': 'test',
        'device_blacklist': 'test',
        'mount_point_whitelist': 'test',
        'mount_point_blacklist': 'test',
    }
    c = Disk('disk', None, {}, [instance])

    assert c._file_system_whitelist == re.compile('test', re.I)
    assert c._file_system_blacklist == re.compile('test|iso9660$', re.I)
    assert c._device_whitelist == re.compile('test', IGNORE_CASE)
    assert c._device_blacklist == re.compile('test', IGNORE_CASE)
    assert c._mount_point_whitelist == re.compile('test', IGNORE_CASE)
    assert c._mount_point_blacklist == re.compile('test', IGNORE_CASE)


def test_ignore_empty_regex():
    instance = {
        'file_system_whitelist': ['test', ''],
        'file_system_blacklist': ['test', ''],
        'device_whitelist': ['test', ''],
        'device_blacklist': ['test', ''],
        'mount_point_whitelist': ['test', ''],
        'mount_point_blacklist': ['test', ''],
    }
    c = Disk('disk', None, {}, [instance])

    assert c._file_system_whitelist == re.compile('test', re.I)
    assert c._file_system_blacklist == re.compile('test|iso9660$', re.I)
    assert c._device_whitelist == re.compile('test', IGNORE_CASE)
    assert c._device_blacklist == re.compile('test', IGNORE_CASE)
    assert c._mount_point_whitelist == re.compile('test', IGNORE_CASE)
    assert c._mount_point_blacklist == re.compile('test', IGNORE_CASE)


def test_exclude_bad_devices():
    c = Disk('disk', None, {}, [{}])

    assert c.exclude_disk(MockPart(device='')) is True
    assert c.exclude_disk(MockPart(device='none')) is True


@requires_windows
def test_exclude_cdrom():
    c = Disk('disk', None, {}, [{}])

    assert c.exclude_disk(MockPart(fstype='ISO9660')) is True
    assert c.exclude_disk(MockPart(opts='rw,cdrom')) is True


def test_file_system_whitelist():
    instance = {'file_system_whitelist': ['ext[34]', 'ntfs']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is False
    assert c.exclude_disk(MockPart(fstype='apfs')) is True


def test_file_system_blacklist():
    instance = {'file_system_blacklist': ['fat']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(fstype='FAT32')) is True
    assert c.exclude_disk(MockPart(fstype='zfs')) is False


def test_file_system_whitelist_blacklist():
    instance = {'file_system_whitelist': ['ext[2-4]'], 'file_system_blacklist': ['ext2']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext2')) is True
    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is True


def test_device_whitelist():
    instance = {'device_whitelist': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(device='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(device='c:\\')) is False
    assert c.exclude_disk(MockPart(device='path\\c:\\')) is True


def test_device_blacklist():
    instance = {'device_blacklist': ['/dev/sda[1-3]']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is False


def test_device_whitelist_blacklist():
    instance = {'device_whitelist': ['/dev/sda[1-3]'], 'device_blacklist': ['/dev/sda3']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True


def test_mount_point_whitelist():
    instance = {'mount_point_whitelist': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(mountpoint='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(mountpoint='c:\\')) is False
    assert c.exclude_disk(MockPart(mountpoint='path\\c:\\')) is True


def test_mount_point_blacklist():
    instance = {'mount_point_blacklist': ['/dev/sda[1-3]']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is False


def test_mount_point_whitelist_blacklist():
    instance = {'mount_point_whitelist': ['/dev/sda[1-3]'], 'mount_point_blacklist': ['/dev/sda3']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True


def test_all_partitions_allow_no_device():
    instance = {'all_partitions': 'true', 'mount_point_blacklist': ['/run$']}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(device='', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='', mountpoint='/run/shm')) is False


def test_legacy_config():
    instance = {
        'excluded_filesystems': ['test', ''],
        'excluded_disks': ['test1', ''],
        'excluded_disk_re': 'test2',
        'excluded_mountpoint_re': 'test',
    }
    c = Disk('disk', None, {}, [instance])

    assert c._file_system_blacklist == re.compile('iso9660$|test$', re.I)
    assert c._device_blacklist == re.compile('test1$|test2', IGNORE_CASE)
    assert c._mount_point_blacklist == re.compile('test', IGNORE_CASE)


def test_legacy_exclude_disk():
    """
    Test legacy exclusion logic config
    """
    instance = {
        'use_mount': 'no',
        'excluded_filesystems': ['aaaaaa'],
        'excluded_mountpoint_re': '^/run$',
        'excluded_disks': ['bbbbbb'],
        'excluded_disk_re': '^tev+$',
    }
    c = Disk('disk', None, {}, [instance])

    # should pass, default mock is a normal disk
    assert c.exclude_disk(MockPart()) is False

    # standard fake devices
    assert c.exclude_disk(MockPart(device='')) is True
    assert c.exclude_disk(MockPart(device='none')) is True
    assert c.exclude_disk(MockPart(device='udev')) is False

    # excluded filesystems list
    assert c.exclude_disk(MockPart(fstype='aaaaaa')) is True
    assert c.exclude_disk(MockPart(fstype='a')) is False

    # excluded devices list
    assert c.exclude_disk(MockPart(device='bbbbbb')) is True
    assert c.exclude_disk(MockPart(device='b')) is False

    # excluded devices regex
    assert c.exclude_disk(MockPart(device='tevvv')) is True
    assert c.exclude_disk(MockPart(device='tevvs')) is False

    # and now with all_partitions
    c._all_partitions = True
    assert c.exclude_disk(MockPart(device='')) is False
    assert c.exclude_disk(MockPart(device='none')) is False
    assert c.exclude_disk(MockPart(device='udev')) is False
    # excluded mountpoint regex
    assert c.exclude_disk(MockPart(device='sdz', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='sdz', mountpoint='/run/shm')) is False


def test_legacy_device_exclusion_logic_no_name():
    instance = {'use_mount': 'yes', 'excluded_mountpoint_re': '^/run$', 'all_partitions': 'yes'}
    c = Disk('disk', None, {}, [instance])

    assert c.exclude_disk(MockPart(device='', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='', mountpoint='/run/shm')) is False
