# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
import os
import re

import pytest
import mock

from datadog_checks.disk import Disk

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DEVICE_NAME = '/dev/sda1'
DISK_GAUGES = [
    'system.disk.free',
    'system.disk.in_use',
    'system.disk.total',
    'system.disk.used',
]
DISK_RATES = [
    'system.disk.write_time_pct',
    'system.disk.read_time_pct',
]
INODE_GAUGES = [
    'system.fs.inodes.total',
    'system.fs.inodes.used',
    'system.fs.inodes.free',
    'system.fs.inodes.in_use'
]
GAUGES_VALUES = {
    'system.disk.total': 5,
    'system.disk.used': 4,
    'system.disk.free': 1,
    'system.disk.in_use': .80,
    'system.fs.inodes.total': 10,
    'system.fs.inodes.used': 1,
    'system.fs.inodes.free': 9,
    'system.fs.inodes.in_use': .10
}
RATES_VALUES = {
    'system.disk.write_time_pct': 9.0,
    'system.disk.read_time_pct': 5.0,
}


class MockPart(object):
    def __init__(self, device=DEFAULT_DEVICE_NAME, fstype='ext4', mountpoint='/', opts='ro'):
        self.device = device
        self.fstype = fstype
        self.mountpoint = mountpoint
        self.opts = opts


class MockDiskMetrics(object):
    total = 5 * 1024
    used = 4 * 1024
    free = 1 * 1024
    percent = 80
    read_time = 50
    write_time = 90


class MockDiskIOMetrics(dict):
    def __init__(self, device=DEFAULT_DEVICE_NAME):
        super(MockDiskIOMetrics, self).__init__()
        self[device] = MockDiskMetrics()


class MockInodesMetrics(object):
    f_files = 10
    f_ffree = 9


class MockIoCountersMetrics(object):
    read_time = 15
    write_time = 25


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

@pytest.fixture(scope="module")
def psutil_mocks():
    p1 = mock.patch('psutil.disk_partitions', return_value=[MockPart()],
                    __name__="disk_partitions")
    p2 = mock.patch('psutil.disk_usage', return_value=MockDiskMetrics(),
                    __name__="disk_usage")
    p3 = mock.patch('os.statvfs', return_value=MockInodesMetrics(),
                    __name__="statvfs")
    p4 = mock.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics())

    yield p1.start(), p2.start(), p3.start(), p4.start()

    p1.stop()
    p2.stop()
    p3.stop()
    p4.stop()

def test_bad_config():
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        Disk('disk', None, {}, [{}, {}])

def test_default_options():
    check = Disk('disk', None, {}, [{}])

    assert check._use_mount is False
    assert check._excluded_filesystems == ['iso9660']
    assert check._excluded_disks == []
    assert check._tag_by_filesystem is False
    assert check._all_partitions is False
    assert check._excluded_disk_re == re.compile('^$')
    assert check._device_tag_re == []
    assert check._service_check_rw is False

def test_disk_check(aggregator):
    """
    Basic check to see if all metrics are there
    """
    c = Disk('disk', None, {}, [{'use_mount': 'no'}])
    c.check({'use_mount': 'no'})
    for name in DISK_GAUGES + INODE_GAUGES + DISK_RATES:
        aggregator.assert_metric(name, tags=[])

    assert aggregator.metrics_asserted_pct == 100.0

def test__exclude_disk_psutil():
    """
    Test exclusion logic
    """
    instances = [{
        'use_mount': 'no',
        'excluded_filesystems': ['aaaaaa'],
        'excluded_mountpoint_re': '^/run$',
        'excluded_disks': ['bbbbbb'],
        'excluded_disk_re': '^tev+$'
    }]
    c = Disk('disk', None, {}, instances)

    # should pass, default mock is a normal disk
    assert c._exclude_disk_psutil(MockPart()) is False

    # standard fake devices
    assert c._exclude_disk_psutil(MockPart(device='')) is True
    assert c._exclude_disk_psutil(MockPart(device='none')) is True
    assert c._exclude_disk_psutil(MockPart(device='udev')) is False

    # excluded filesystems list
    assert c._exclude_disk_psutil(MockPart(fstype='aaaaaa')) is True
    assert c._exclude_disk_psutil(MockPart(fstype='a')) is False

    # excluded devices list
    assert c._exclude_disk_psutil(MockPart(device='bbbbbb')) is True
    assert c._exclude_disk_psutil(MockPart(device='b')) is False

    # excluded devices regex
    assert c._exclude_disk_psutil(MockPart(device='tevvv')) is True
    assert c._exclude_disk_psutil(MockPart(device='tevvs')) is False

    # and now with all_partitions
    c._all_partitions = True
    assert c._exclude_disk_psutil(MockPart(device='')) is False
    assert c._exclude_disk_psutil(MockPart(device='none')) is False
    assert c._exclude_disk_psutil(MockPart(device='udev')) is False
    # excluded mountpoint regex
    assert c._exclude_disk_psutil(MockPart(device='sdz', mountpoint='/run')) is True
    assert c._exclude_disk_psutil(MockPart(device='sdz', mountpoint='/run/shm')) is False

def test_device_exclusion_logic_no_name():
    """
    Same as above but with default configuration values and device='' to expose a bug in #2359
    """
    instances = [{
        'use_mount': 'yes',
        'excluded_mountpoint_re': '^/run$',
        'all_partitions': 'yes'
    }]
    c = Disk('disk', None, {}, instances)

    assert c._exclude_disk_psutil(MockPart(device='', mountpoint='/run')) is True
    assert c._exclude_disk_psutil(MockPart(device='', mountpoint='/run/shm')) is False

def test_psutil(aggregator, psutil_mocks):
    """
    Mock psutil and run the check
    """
    for tag_by in ['yes', 'no']:
        instances = [{'tag_by_filesystem': tag_by}]
        c = Disk('disk', None, {}, instances)
        c.check(instances[0])

        tags = ['ext4', 'filesystem:ext4', 'device:{}'.format(DEFAULT_DEVICE_NAME)] if tag_by == 'yes' else []

        for name, value in GAUGES_VALUES.iteritems():
            aggregator.assert_metric(name, value=value, tags=tags)

        for name, value in RATES_VALUES.iteritems():
            aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])

    assert aggregator.metrics_asserted_pct == 100.0

def test_use_mount(aggregator, psutil_mocks):
    """
    Same as above, using mount to tag
    """
    instances = [{'use_mount': 'yes'}]
    c = Disk('disk', None, {}, instances)
    c.check(instances[0])

    for name, value in GAUGES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=['device:/'])

    for name, value in RATES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])

    assert aggregator.metrics_asserted_pct == 100.0

def test_psutil_rw(aggregator, psutil_mocks):
    """
    Check for 'ro' option in the mounts
    """
    instances = [{'service_check_rw': 'yes'}]
    c = Disk('disk', None, {}, instances)
    c.check(instances[0])

    aggregator.assert_service_check('disk.read_write', status=Disk.CRITICAL)

def mock_df_output(fname):
    """
    Load fixtures from tests/fixtures/ folder and return a tuple matching the
    return value of `get_subprocess_output`
    """
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read(), '', ''

def test_no_psutil_debian(aggregator):
    p1 = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__="statvfs")
    p2 = mock.patch('datadog_checks.disk.disk.get_subprocess_output',
                    return_value=mock_df_output('debian-df-Tk'), __name__="get_subprocess_output")
    p1.start()
    p2.start()

    instances = [{'use_mount': 'no', 'excluded_filesystems': ['tmpfs']}]
    c = Disk('disk', None, {}, instances)
    c._psutil = lambda: False  # disable psutil
    c.check(instances[0])

    for name, value in GAUGES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])
        # backward compatibility with the old check
        aggregator.assert_metric(name, tags=['device:udev'])
    assert aggregator.metrics_asserted_pct == 100.0

def test_no_psutil_freebsd(aggregator):
    p1 = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__="statvfs")
    p2 = mock.patch('datadog_checks.disk.disk.get_subprocess_output',
                    return_value=mock_df_output('freebsd-df-Tk'), __name__="get_subprocess_output")
    p1.start()
    p2.start()

    instances = [{'use_mount': 'no', 'excluded_filesystems': ['devfs'], 'excluded_disk_re': 'zroot/.+'}]
    c = Disk('disk', None, {}, instances)
    c._psutil = lambda: False  # disable psutil
    c.check(instances[0])

    for name, value in GAUGES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=['device:zroot'])
    assert aggregator.metrics_asserted_pct == 100.0

def test_no_psutil_centos(aggregator):
    p1 = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__="statvfs")
    p2 = mock.patch('datadog_checks.disk.disk.get_subprocess_output',
                    return_value=mock_df_output('centos-df-Tk'), __name__="get_subprocess_output")
    p1.start()
    p2.start()

    instances = [{'use_mount': 'no', 'excluded_filesystems': ['devfs', 'tmpfs'], 'excluded_disks': ['/dev/sda1']}]
    c = Disk('disk', None, {}, instances)
    c._psutil = lambda: False  # disable psutil
    c.check(instances[0])

    for device in ['/dev/sda3', '10.1.5.223:/vil/cor']:
        for name, _ in GAUGES_VALUES.iteritems():
            aggregator.assert_metric(name, tags=['device:{}'.format(device)])
    assert aggregator.metrics_asserted_pct == 100.0

def test_legacy_option():
    """
    Ensure check option overrides datadog.conf
    """
    c = Disk('disk', None, {'use_mount': 'yes'}, [{}])
    assert c._use_mount is True

    c = Disk('disk', None, {'use_mount': 'yes'}, [{'use_mount': 'no'}])
    assert c._use_mount is False

def test_ignore_empty_regex():
    """
    Ignore empty regex as they match all strings
    (and so exclude all disks from the check)
    """
    check = Disk('disk', None, {'device_blacklist_re': ''}, [{}])
    assert check._excluded_disk_re == re.compile('^$')

def test_device_tagging(aggregator, psutil_mocks):
    instances = [{'use_mount': 'no', 'device_tag_re': {"/dev/sda.*": "type:dev,tag:two"}, 'tags':["optional:tags1"]}]
    c = Disk('disk', None, {}, instances)
    c.check(instances[0])

    # Assert metrics
    tags = ["type:dev", "tag:two", "device:{}".format(DEFAULT_DEVICE_NAME), "optional:tags1"]
    for name, value in GAUGES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=tags)

    for name, value in RATES_VALUES.iteritems():
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME), "optional:tags1"])

    assert aggregator.metrics_asserted_pct == 100.0
