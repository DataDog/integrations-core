# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from itertools import chain

import mock
import pytest

from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.timeout import TimeoutException
from datadog_checks.dev.testing import requires_linux, requires_windows
from datadog_checks.dev.utils import ON_WINDOWS, get_metadata_metrics, mock_context_manager
from datadog_checks.disk import Disk
from datadog_checks.disk.disk import IGNORE_CASE

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

HERE = os.path.dirname(os.path.abspath(__file__))


def mock_blkid_output():
    """
    Load fixtures from tests/fixtures/ folder and return a tuple matching the
    return value of `get_subprocess_output`
    """
    with open(os.path.join(HERE, 'fixtures', 'blkid')) as f:
        return f.read(), '', ''


def mock_lsblk_output():
    """
    Load fixtures from tests/fixtures/ folder and return a tuple matching the
    return value of `get_subprocess_output`
    """
    with open(os.path.join(HERE, 'fixtures', 'lsblk'), 'r') as f:
        return f.read(), '', ''


def mock_blkid_cache_file():
    return os.path.join(HERE, 'fixtures', 'blkid_cache_file')


def mock_blkid_cache_file_no_label():
    return os.path.join(HERE, 'fixtures', 'blkid_cache_file_no_label')


class MockPart:
    def __init__(
        self, device=DEFAULT_DEVICE_NAME, fstype=DEFAULT_FILE_SYSTEM, mountpoint=DEFAULT_MOUNT_POINT, opts='ro'
    ):
        self.device = device
        self.fstype = fstype
        self.mountpoint = mountpoint
        self.opts = opts


class MockDiskMetrics:
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


class MockInodesMetrics:
    f_files = 10
    f_ffree = 9


class MockIoCountersMetrics:
    read_time = 15
    write_time = 25


@pytest.fixture(scope='session')
def instance_blkid_cache_file():
    return {'blkid_cache_file': mock_blkid_cache_file()}


@pytest.fixture(scope='session')
def instance_blkid_cache_file_no_label():
    return {'blkid_cache_file': mock_blkid_cache_file_no_label()}


@pytest.fixture
def psutil_mocks():
    if ON_WINDOWS:
        mock_statvfs = mock_context_manager()
    else:
        mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')

    with (
        mock.patch('psutil.disk_partitions', return_value=[MockPart()], __name__='disk_partitions'),
        mock.patch('psutil.disk_usage', return_value=MockDiskMetrics(), __name__='disk_usage'),
        mock.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics()),
        mock_statvfs,
    ):
        yield


def test_default_options():
    check = Disk('disk', {}, [{}])

    assert check._use_mount is False
    assert check._all_partitions is False
    assert check._file_system_include is None
    assert check._file_system_exclude == re.compile('iso9660$|tracefs$', re.I)
    assert check._device_include is None
    assert check._device_exclude is None
    assert check._mount_point_include is None
    assert check._mount_point_exclude == re.compile('(/host)?/proc/sys/fs/binfmt_misc$', IGNORE_CASE)
    assert check._tag_by_filesystem is False
    assert check._device_tag_re == []
    assert check._service_check_rw is False
    assert check._min_disk_size == 0
    assert check._timeout == 5


def test_bad_config():
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        Disk('disk', {}, [{}, {}])


@pytest.mark.usefixtures('psutil_mocks')
def test_default(aggregator, gauge_metrics, rate_metrics, count_metrics, dd_run_check):
    """
    Mock psutil and run the check
    """
    for tag_by in ['true', 'false']:
        instance = {'tag_by_filesystem': tag_by, 'tag_by_label': False}
        c = Disk('disk', {}, [instance])
        dd_run_check(c)

        if tag_by == 'true':
            tags = [
                DEFAULT_FILE_SYSTEM,
                'filesystem:{}'.format(DEFAULT_FILE_SYSTEM),
                'device:{}'.format(DEFAULT_DEVICE_NAME),
                'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
            ]
        else:
            tags = []

        for name, value in gauge_metrics.items():
            aggregator.assert_metric(name, value=value, count=1, metric_type=aggregator.GAUGE, tags=tags)

        for name, value in rate_metrics.items():
            aggregator.assert_metric(
                name,
                value=value,
                count=1,
                metric_type=aggregator.RATE,
                tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
            )

        for name, value in count_metrics.items():
            aggregator.assert_metric(
                name,
                value=value,
                count=1,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
            )

        aggregator.assert_all_metrics_covered()
        aggregator.reset()


@pytest.mark.usefixtures('psutil_mocks')
def test_rw(aggregator, dd_run_check):
    """
    Check for 'ro' option in the mounts
    """
    instance = {'service_check_rw': 'yes', 'tag_by_label': False}
    c = Disk('disk', {}, [instance])
    dd_run_check(c)

    aggregator.assert_service_check('disk.read_write', status=Disk.CRITICAL)


@pytest.mark.usefixtures('psutil_mocks')
def test_use_mount(aggregator, instance_basic_mount, gauge_metrics, rate_metrics, count_metrics, dd_run_check):
    """
    Same as above, using mount to tag
    """
    c = Disk('disk', {}, [instance_basic_mount])
    dd_run_check(c)

    for name, value in gauge_metrics.items():
        aggregator.assert_metric(
            name,
            value=value,
            tags=['device:{}'.format(DEFAULT_MOUNT_POINT), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
        )

    for name, value in chain(rate_metrics.items(), count_metrics.items()):
        aggregator.assert_metric(
            name,
            value=value,
            tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_linux  # Only linux cares about upper/lower case for paths.
@pytest.mark.parametrize(
    'lc_device_tag, expected_dev_path',
    [
        pytest.param(None, '//CIFS/DEV1', id='Default behavior, keep case'),
        pytest.param(False, '//CIFS/DEV1', id='Disabled, keep case'),
        pytest.param(True, '//cifs/dev1', id='Enabled, lowercase'),
    ],
)
def test_lowercase_device_tag(
    aggregator,
    instance_basic_volume,
    gauge_metrics,
    rate_metrics,
    count_metrics,
    dd_run_check,
    mocker,
    lc_device_tag,
    expected_dev_path,
):
    """
    If explicitly configured, we will lowercase the "device" tag value.

    For metrics with uppercase "device" tag values, our backend introduces a lowercase version of the tag.
    Some customers don't like this and cannot use the "device_name" tag instead.
    They requested that we add a switch for them to lowercase the "device" tag before we submit it.
    This flag MUST be off by default to avoid breaking anyone else.
    """
    if lc_device_tag is not None:
        instance_basic_volume['lowercase_device_tag'] = lc_device_tag
    c = Disk('disk', {}, [instance_basic_volume])

    if ON_WINDOWS:
        mock_statvfs = mock_context_manager()
    else:
        mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')

    full_dev_path = '//CIFS/DEV1'
    mocker.patch(
        'psutil.disk_partitions',
        return_value=[MockPart(device=full_dev_path, fstype="cifs")],
        __name__='disk_partitions',
    )
    mocker.patch('psutil.disk_usage', return_value=MockDiskMetrics(), __name__='disk_usage')
    mocker.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics(full_dev_path))
    with mock_statvfs:
        dd_run_check(c)

    for name in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric_has_tag(name, f'device:{expected_dev_path}')
        # Make sure the "device_name" tag isn't affected.
        aggregator.assert_metric_has_tag(name, 'device_name:DEV1')


@pytest.mark.usefixtures('psutil_mocks')
def test_device_tagging(aggregator, gauge_metrics, rate_metrics, count_metrics, dd_run_check):
    instance = {
        'use_mount': 'no',
        'device_tag_re': {'{}.*'.format(DEFAULT_DEVICE_NAME[:-1]): 'type:dev,tag:two'},
        'tags': ['optional:tags1'],
        'tag_by_label': False,
    }
    c = Disk('disk', {}, [instance])

    with mock.patch('datadog_checks.disk.disk.Disk._get_devices_label'):
        # _get_devices_label is only called on linux, so devices_label is manually filled
        # to make the test run on everything
        c.devices_label = {DEFAULT_DEVICE_NAME: ['label:mylab', 'device_label:mylab']}
        dd_run_check(c)

    # Assert metrics
    tags = [
        'type:dev',
        'tag:two',
        'device:{}'.format(DEFAULT_DEVICE_NAME),
        'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
        'optional:tags1',
        'label:mylab',
        'device_label:mylab',
    ]

    for name, value in chain(gauge_metrics.items(), rate_metrics.items(), count_metrics.items()):
        aggregator.assert_metric(
            name,
            value=value,
            tags=tags,
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_get_devices_label():
    c = Disk('disk', {}, [{}])

    with mock.patch(
        "datadog_checks.disk.disk.get_subprocess_output",
        return_value=mock_blkid_output(),
        __name__='get_subprocess_output',
    ):
        labels = c._get_devices_label()
        assert labels.get("/dev/mapper/vagrant--vg-root") == ["label:DATA", "device_label:DATA"]


def test_lsblk_blkid_cache_incompatible():
    """
    Verify that `use_lsblk` and `blkid_cache_file` can't be used at the same time.
    """
    with pytest.raises(Exception, match="Only one of 'use_lsblk' and 'blkid_cache_file' can be set at the same time."):
        Disk('disk', {}, [{'use_lsblk': True, 'blkid_cache_file': 'filepath'}])


def test_get_devices_label_options():
    """
    Verify that
       - use_lsblk uses lsblk for labels,
       - blkid_cache_file not null makes it use the blkid_cache and
       - by default we use the blkid command.
    """
    c_lsblk = Disk('disk', {}, [{'use_lsblk': True}])
    c_blkid = Disk('disk', {}, [{}])
    c_blkid_cache = Disk('disk', {}, [{'blkid_cache_file': 'filepath'}])

    prefix_fun = "datadog_checks.disk.disk.Disk._get_devices_label_from_"
    with (
        mock.patch(prefix_fun + "lsblk", return_value="lsblk"),
        mock.patch(prefix_fun + "blkid", return_value="blkid"),
        mock.patch(prefix_fun + "blkid_cache", return_value="blkid_cache"),
    ):
        assert c_lsblk._get_devices_label() == "lsblk"
        assert c_blkid._get_devices_label() == "blkid"
        assert c_blkid_cache._get_devices_label() == "blkid_cache"


def test_get_devices_label_from_lsblk():
    """
    Test lsblk output parsing.
    """
    c = Disk('disk', {}, [{}])

    with mock.patch(
        "datadog_checks.disk.disk.get_subprocess_output",
        return_value=mock_lsblk_output(),
        __name__='get_subprocess_output',
    ):
        labels = c._get_devices_label_from_lsblk()

    assert labels == {
        "/dev/sda1": ["label:MYLABEL", "device_label:MYLABEL"],
        "/dev/sda15": ["label: WITH SPACES ", "device_label: WITH SPACES "],
    }


@pytest.mark.usefixtures('psutil_mocks')
def test_min_disk_size(aggregator, gauge_metrics, rate_metrics, count_metrics, dd_run_check):
    instance = {'min_disk_size': 0.001}
    c = Disk('disk', {}, [instance])

    m = MockDiskMetrics()
    m.total = 0
    with mock.patch('psutil.disk_usage', return_value=m, __name__='disk_usage'):
        dd_run_check(c)

    for name in gauge_metrics:
        aggregator.assert_metric(name, count=0)

    for name in rate_metrics:
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    for name in count_metrics:
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_labels_from_blkid_cache_file(
    aggregator,
    instance_blkid_cache_file,
    gauge_metrics,
    rate_metrics,
    count_metrics,
    dd_run_check,
):
    """
    Verify that the disk labels are set when the blkid_cache_file option is set
    """
    c = Disk('disk', {}, [instance_blkid_cache_file])
    dd_run_check(c)
    for metric in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric(
            metric, tags=['device:/dev/sda1', 'device_name:sda1', 'label:MYLABEL', 'device_label:MYLABEL']
        )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_blkid_cache_file_contains_no_labels(
    aggregator,
    instance_blkid_cache_file_no_label,
    gauge_metrics,
    rate_metrics,
    count_metrics,
    dd_run_check,
):
    """
    Verify that the disk labels are ignored if the cache file doesn't contain any
    """
    c = Disk('disk', {}, [instance_blkid_cache_file_no_label])
    dd_run_check(c)
    for metric in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric(metric, tags=['device:/dev/sda1', 'device_name:sda1'])
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('psutil_mocks')
def test_timeout_config(aggregator, dd_run_check):
    """Test timeout configuration value is used on every timeout on the check."""

    # Arbitrary value
    TIMEOUT_VALUE = 42
    instance = {'timeout': TIMEOUT_VALUE}
    c = Disk('disk', {}, [instance])

    # Mock timeout version
    def no_timeout(fun):
        return lambda *args: fun(args)

    with (
        mock.patch('psutil.disk_partitions', return_value=[MockPart()]),
        mock.patch('datadog_checks.disk.disk.timeout', return_value=no_timeout) as mock_timeout,
    ):
        dd_run_check(c)

    mock_timeout.assert_called_with(TIMEOUT_VALUE)


@pytest.mark.usefixtures('psutil_mocks')
def test_timeout_warning(aggregator, gauge_metrics, rate_metrics, count_metrics, dd_run_check):
    """Test a warning is raised when there is a Timeout exception."""

    # Raise exception for "/faulty" mountpoint
    def faulty_timeout(fun):
        def f(mountpoint):
            if mountpoint == "/faulty":
                raise TimeoutException
            else:
                return fun(mountpoint)

        return f

    c = Disk('disk', {}, [{}])
    c.log = mock.MagicMock()
    m = MockDiskMetrics()
    m.total = 0

    with (
        mock.patch('psutil.disk_partitions', return_value=[MockPart(), MockPart(mountpoint="/faulty")]),
        mock.patch('psutil.disk_usage', return_value=m, __name__='disk_usage'),
        mock.patch('datadog_checks.disk.disk.timeout', return_value=faulty_timeout),
    ):
        dd_run_check(c)

    # Check that the warning is called once for the faulty disk
    c.log.warning.assert_called_once()

    for name in gauge_metrics:
        aggregator.assert_metric(name, count=0)

    for name in chain(rate_metrics, count_metrics):
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('psutil_mocks')
def test_include_all_devices(aggregator, gauge_metrics, rate_metrics, dd_run_check):
    c = Disk('disk', {}, [{}])

    with mock.patch('psutil.disk_partitions', return_value=[]) as m:
        dd_run_check(c)
        # By default, we include all devices
        m.assert_called_with(all=True)

    instance = {'include_all_devices': False}
    c = Disk('disk', {}, [instance])

    with mock.patch('psutil.disk_partitions', return_value=[]) as m:
        dd_run_check(c)
        m.assert_called_with(all=False)


def test_default_casing():
    if ON_WINDOWS:
        assert IGNORE_CASE == re.I
    else:
        assert IGNORE_CASE == 0


def test_default_mock():
    c = Disk('disk', {}, [{}])

    assert c.exclude_disk(MockPart()) is False


def assert_regex_equal(a, b):
    assert a.pattern == b.pattern
    assert a.flags == b.flags


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


def test_bad_config_string_regex_deprecated():
    instance = {
        'file_system_whitelist': 'test',
        'file_system_blacklist': 'test',
        'device_whitelist': 'test',
        'device_blacklist': 'test',
        'mount_point_whitelist': 'test',
        'mount_point_blacklist': 'test',
    }
    c = Disk('disk', {}, [instance])

    assert_regex_equal(c._file_system_include, re.compile('test', re.I))
    assert_regex_equal(c._file_system_exclude, re.compile('test|iso9660$|tracefs$', re.I))
    assert_regex_equal(c._device_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._device_exclude, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_exclude, re.compile('test|(/host)?/proc/sys/fs/binfmt_misc$', IGNORE_CASE))


def test_ignore_empty_regex_deprecated():
    instance = {
        'file_system_whitelist': ['test', ''],
        'file_system_blacklist': ['test', ''],
        'device_whitelist': ['test', ''],
        'device_blacklist': ['test', ''],
        'mount_point_whitelist': ['test', ''],
        'mount_point_blacklist': ['test', ''],
    }
    c = Disk('disk', {}, [instance])

    assert_regex_equal(c._file_system_include, re.compile('test', re.I))
    assert_regex_equal(c._file_system_exclude, re.compile('test|iso9660$|tracefs$', re.I))
    assert_regex_equal(c._device_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._device_exclude, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_include, re.compile('test', IGNORE_CASE))
    assert_regex_equal(c._mount_point_exclude, re.compile('test|(/host)?/proc/sys/fs/binfmt_misc$', IGNORE_CASE))


def test_file_system_whitelist_deprecated():
    instance = {'file_system_whitelist': ['ext[34]', 'ntfs']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is False
    assert c.exclude_disk(MockPart(fstype='apfs')) is True


def test_file_system_blacklist_deprecated():
    instance = {'file_system_blacklist': ['fat']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='FAT32')) is True
    assert c.exclude_disk(MockPart(fstype='zfs')) is False


def test_file_system_whitelist_blacklist_deprecated():
    instance = {'file_system_whitelist': ['ext[2-4]'], 'file_system_blacklist': ['ext2']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(fstype='ext2')) is True
    assert c.exclude_disk(MockPart(fstype='ext3')) is False
    assert c.exclude_disk(MockPart(fstype='ext4')) is False
    assert c.exclude_disk(MockPart(fstype='NTFS')) is True


def test_device_whitelist_deprecated():
    instance = {'device_whitelist': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(device='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(device='c:\\')) is False
    assert c.exclude_disk(MockPart(device='path\\c:\\')) is True


def test_device_blacklist_deprecated():
    instance = {'device_blacklist': ['/dev/sda[1-3]']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is False


def test_device_whitelist_blacklist_deprecated():
    instance = {'device_whitelist': ['/dev/sda[1-3]'], 'device_blacklist': ['/dev/sda3']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(device='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(device='/dev/sda4')) is True


def test_mount_point_whitelist_deprecated():
    instance = {'mount_point_whitelist': ['/dev/sda[1-3]', 'c:']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True
    assert c.exclude_disk(MockPart(mountpoint='path/dev/sda1')) is True

    assert c.exclude_disk(MockPart(mountpoint='c:\\')) is False
    assert c.exclude_disk(MockPart(mountpoint='path\\c:\\')) is True


def test_mount_point_blacklist_deprecated():
    instance = {'mount_point_blacklist': ['/dev/sda[1-3]']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is False


def test_mount_point_whitelist_blacklist_deprecated():
    instance = {'mount_point_whitelist': ['/dev/sda[1-3]'], 'mount_point_blacklist': ['/dev/sda3']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(mountpoint='/dev/sda1')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda2')) is False
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda3')) is True
    assert c.exclude_disk(MockPart(mountpoint='/dev/sda4')) is True


def test_all_partitions_allow_no_device_deprecated():
    instance = {'all_partitions': 'true', 'mount_point_blacklist': ['/run$']}
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='', mountpoint='/run/shm')) is False


def test_legacy_config():
    instance = {
        'excluded_filesystems': ['test', ''],
        'excluded_disks': ['test1', ''],
        'excluded_disk_re': 'test2',
        'excluded_mountpoint_re': 'test',
    }
    c = Disk('disk', {}, [instance])

    assert_regex_equal(c._file_system_exclude, re.compile('iso9660$|tracefs$|test$', re.I))
    assert_regex_equal(c._device_exclude, re.compile('test1$|test2', IGNORE_CASE))
    assert_regex_equal(c._mount_point_exclude, re.compile('(/host)?/proc/sys/fs/binfmt_misc$|test', IGNORE_CASE))


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
    c = Disk('disk', {}, [instance])

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
    c = Disk('disk', {}, [instance])

    assert c.exclude_disk(MockPart(device='', mountpoint='/run')) is True
    assert c.exclude_disk(MockPart(device='', mountpoint='/run/shm')) is False
