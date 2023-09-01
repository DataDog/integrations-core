# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.dev.testing import requires_windows
from datadog_checks.dev.utils import ON_WINDOWS
from datadog_checks.disk.disk import IGNORE_CASE, Disk

from .mocks import MockPart
from .utils import assert_regex_equal


def test_default_casing():
    if ON_WINDOWS:
        assert IGNORE_CASE == re.I
    else:
        assert IGNORE_CASE == 0


def test_default_mock():
    c = Disk('disk', {}, [{}])

    assert c.exclude_disk(MockPart()) is False


def test_bad_config_string_regex():
    instance = {
        'file_system_include': 'test',
        'file_system_exclude': 'test',
        'device_include': 'test',
        'device_exclude': 'test',
        'mount_point_include': 'test',
        'mount_point_exclude': 'test',
    }
    c = Disk('disk', {}, [instance])

    assert_regex_equal(c._file_system_include, re.compile('test', re.I))
    assert_regex_equal(c._file_system_exclude, re.compile('test|iso9660$|tracefs$', re.I))
    assert_regex_equal(c._device_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._device_exclude, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_exclude, re.compile('test|(/host)?/proc/sys/fs/binfmt_misc$', IGNORE_CASE))


def test_ignore_empty_regex():
    instance = {
        'file_system_include': ['test', ''],
        'file_system_exclude': ['test', ''],
        'device_include': ['test', ''],
        'device_exclude': ['test', ''],
        'mount_point_include': ['test', ''],
        'mount_point_exclude': ['test', ''],
    }
    c = Disk('disk', {}, [instance])

    assert_regex_equal(c._file_system_include, re.compile('test', re.I))
    assert_regex_equal(c._file_system_exclude, re.compile('test|iso9660$|tracefs$', re.I))
    assert_regex_equal(c._device_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._device_exclude, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_exclude, re.compile('test|(/host)?/proc/sys/fs/binfmt_misc$', IGNORE_CASE))


def test_exclude_bad_devices():
    c = Disk('disk', {}, [{}])

    assert c.exclude_disk(MockPart(device='')) is True
    assert c.exclude_disk(MockPart(device='none')) is True


@requires_windows
def test_exclude_cdrom():
    c = Disk('disk', {}, [{}])

    assert c.exclude_disk(MockPart(fstype='ISO9660')) is True
    assert c.exclude_disk(MockPart(opts='rw,cdrom')) is True


def test_file_system_include():
    instance = {'file_system_include': ['ext[34]', 'ntfs']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is False
    assert c.exclude_disk(MockPart(fstype='apfs')) is True


def test_file_system_exclude():
    instance = {'file_system_exclude': ['fat']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='FAT32')) is True
    assert c.exclude_disk(MockPart(fstype='zfs')) is False


def test_file_system_include_exclude():
    instance = {'file_system_include': ['ext[2-4]'], 'file_system_exclude': ['ext2']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext2')) is True
    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is True


def test_device_include():
    instance = {'device_include': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(device='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(device='c:\\')) is False
    assert c.exclude_disk(MockPart(device='path\\c:\\')) is True


def test_device_exclude():
    instance = {'device_exclude': ['/dev/sda[1-3]']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is False


def test_device_include_exclude():
    instance = {'device_include': ['/dev/sda[1-3]'], 'device_exclude': ['/dev/sda3']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True


def test_mount_point_include():
    instance = {'mount_point_include': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(mountpoint='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(mountpoint='c:\\')) is False
    assert c.exclude_disk(MockPart(mountpoint='path\\c:\\')) is True


def test_mount_point_exclude():
    instance = {'mount_point_exclude': ['/dev/sda[1-3]']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is False


def test_mount_point_include_exclude():
    instance = {'mount_point_include': ['/dev/sda[1-3]'], 'mount_point_exclude': ['/dev/sda3']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True


def test_all_partitions_allow_no_device():
    instance = {'all_partitions': 'true', 'mount_point_exclude': ['/run$']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='', mountpoint='/run/shm')) is False
