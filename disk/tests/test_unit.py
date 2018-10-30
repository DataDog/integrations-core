# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest
from six import iteritems

from datadog_checks.disk import Disk
from .common import DEFAULT_DEVICE_NAME, DEFAULT_FILE_SYSTEM, DEFAULT_MOUNT_POINT
from .mocks import MockInodesMetrics, MockPart, mock_df_output
from .utils import requires_unix


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


def test_bad_config():
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        Disk('disk', None, {}, [{}, {}])


def test_ignore_empty_regex():
    """
    Ignore empty regex as they match all strings
    (and so exclude all disks from the check)
    """
    check = Disk('disk', None, {'device_blacklist_re': ''}, [{}])
    assert check._excluded_disk_re == re.compile('^$')


def test__exclude_disk_psutil():
    """
    Test exclusion logic
    """
    instance = {
        'use_mount': 'no',
        'excluded_filesystems': ['aaaaaa'],
        'excluded_mountpoint_re': '^/run$',
        'excluded_disks': ['bbbbbb'],
        'excluded_disk_re': '^tev+$'
    }
    c = Disk('disk', None, {}, [instance])

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
    instance = {
        'use_mount': 'yes',
        'excluded_mountpoint_re': '^/run$',
        'all_partitions': 'yes'
    }
    c = Disk('disk', None, {}, [instance])

    assert c._exclude_disk_psutil(MockPart(device='', mountpoint='/run')) is True
    assert c._exclude_disk_psutil(MockPart(device='', mountpoint='/run/shm')) is False


@pytest.mark.usefixtures('psutil_mocks')
def test_psutil(aggregator, gauge_metrics, rate_metrics):
    """
    Mock psutil and run the check
    """
    for tag_by in ['true', 'false']:
        instance = {'tag_by_filesystem': tag_by}
        c = Disk('disk', None, {}, [instance])
        c.check(instance)

        if tag_by == 'true':
            tags = [
                DEFAULT_FILE_SYSTEM,
                'filesystem:{}'.format(DEFAULT_FILE_SYSTEM),
                'device:{}'.format(DEFAULT_DEVICE_NAME)
            ]
        else:
            tags = []

        for name, value in iteritems(gauge_metrics):
            aggregator.assert_metric(name, value=value, tags=tags)

        for name, value in iteritems(rate_metrics):
            aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks')
def test_psutil_rw(aggregator):
    """
    Check for 'ro' option in the mounts
    """
    instance = {'service_check_rw': 'yes'}
    c = Disk('disk', None, {}, [instance])
    c.check(instance)

    aggregator.assert_service_check('disk.read_write', status=Disk.CRITICAL)


@pytest.mark.usefixtures('psutil_mocks')
def test_use_mount(aggregator, instance_basic_mount, gauge_metrics, rate_metrics):
    """
    Same as above, using mount to tag
    """
    c = Disk('disk', None, {}, [instance_basic_mount])
    c.check(instance_basic_mount)

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_MOUNT_POINT)])

    for name, value in iteritems(rate_metrics):
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks')
def test_device_tagging(aggregator, gauge_metrics, rate_metrics):
    instance = {
        'use_mount': 'no',
        'device_tag_re': {'{}.*'.format(DEFAULT_DEVICE_NAME[:-1]): 'type:dev,tag:two'},
        'tags': ['optional:tags1']
    }
    c = Disk('disk', None, {}, [instance])
    c.check(instance)

    # Assert metrics
    tags = ['type:dev', 'tag:two', 'device:{}'.format(DEFAULT_DEVICE_NAME), 'optional:tags1']
    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=tags)

    for name, value in iteritems(rate_metrics):
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'optional:tags1'])

    aggregator.assert_all_metrics_covered()


@requires_unix
def test_no_psutil_debian(aggregator, gauge_metrics):
    instance = {'use_mount': 'no', 'excluded_filesystems': ['tmpfs']}
    c = Disk('disk', None, {}, [instance])
    # disable psutil
    c._psutil = lambda: False

    mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')
    mock_output = mock.patch(
        'datadog_checks.disk.disk.get_subprocess_output',
        return_value=mock_df_output('debian-df-Tk'),
        __name__='get_subprocess_output'
    )

    with mock_statvfs, mock_output:
        c.check(instance)

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=['device:{}'.format(DEFAULT_DEVICE_NAME)])
        # backward compatibility with the old check
        aggregator.assert_metric(name, tags=['device:udev'])

    aggregator.assert_all_metrics_covered()


@requires_unix
def test_no_psutil_freebsd(aggregator, gauge_metrics):
    instance = {'use_mount': 'no', 'excluded_filesystems': ['devfs'], 'excluded_disk_re': 'zroot/.+'}
    c = Disk('disk', None, {}, [instance])
    # disable psutil
    c._psutil = lambda: False

    mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')
    mock_output = mock.patch(
        'datadog_checks.disk.disk.get_subprocess_output',
        return_value=mock_df_output('freebsd-df-Tk'),
        __name__='get_subprocess_output'
    )

    with mock_statvfs, mock_output:
        c.check(instance)

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=['device:zroot'])

    aggregator.assert_all_metrics_covered()


@requires_unix
def test_no_psutil_centos(aggregator, gauge_metrics):
    instance = {'use_mount': 'no', 'excluded_filesystems': ['devfs', 'tmpfs'], 'excluded_disks': ['/dev/sda1']}
    c = Disk('disk', None, {}, [instance])
    # disable psutil
    c._psutil = lambda: False

    mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')
    mock_output = mock.patch(
        'datadog_checks.disk.disk.get_subprocess_output',
        return_value=mock_df_output('centos-df-Tk'),
        __name__='get_subprocess_output'
    )

    with mock_statvfs, mock_output:
        c.check(instance)

    for device in ['/dev/sda3', '10.1.5.223:/vil/cor']:
        for name in gauge_metrics:
            aggregator.assert_metric(name, tags=['device:{}'.format(device)])

    aggregator.assert_all_metrics_covered()
