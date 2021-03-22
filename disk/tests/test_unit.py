# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from itertools import chain

import mock
import pytest
from six import iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.timeout import TimeoutException
from datadog_checks.disk import Disk
from datadog_checks.disk.disk import IGNORE_CASE

from .common import DEFAULT_DEVICE_BASE_NAME, DEFAULT_DEVICE_NAME, DEFAULT_FILE_SYSTEM, DEFAULT_MOUNT_POINT
from .mocks import MockDiskMetrics, MockPart, mock_blkid_output


def test_default_options():
    check = Disk('disk', {}, [{}])

    assert check._use_mount is False
    assert check._all_partitions is False
    assert check._file_system_include is None
    assert check._file_system_exclude == re.compile('iso9660$', re.I)
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


@pytest.mark.usefixtures('psutil_mocks', 'timeout_mock')
def test_default(aggregator, gauge_metrics, rate_metrics, count_metrics):
    """
    Mock psutil and run the check
    """
    for tag_by in ['true', 'false']:
        instance = {'tag_by_filesystem': tag_by, 'tag_by_label': False}
        c = Disk('disk', {}, [instance])
        c.check(instance)

        if tag_by == 'true':
            tags = [
                DEFAULT_FILE_SYSTEM,
                'filesystem:{}'.format(DEFAULT_FILE_SYSTEM),
                'device:{}'.format(DEFAULT_DEVICE_NAME),
                'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
            ]
        else:
            tags = []

        for name, value in iteritems(gauge_metrics):
            aggregator.assert_metric(name, value=value, count=1, metric_type=aggregator.GAUGE, tags=tags)

        for name, value in iteritems(rate_metrics):
            aggregator.assert_metric(
                name,
                value=value,
                count=1,
                metric_type=aggregator.RATE,
                tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
            )

        for name, value in iteritems(count_metrics):
            aggregator.assert_metric(
                name,
                value=value,
                count=1,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
            )

        aggregator.assert_all_metrics_covered()
        aggregator.reset()


@pytest.mark.usefixtures('psutil_mocks', 'timeout_mock')
def test_rw(aggregator):
    """
    Check for 'ro' option in the mounts
    """
    instance = {'service_check_rw': 'yes', 'tag_by_label': False}
    c = Disk('disk', {}, [instance])
    c.check(instance)

    aggregator.assert_service_check('disk.read_write', status=Disk.CRITICAL)


@pytest.mark.usefixtures('psutil_mocks', 'timeout_mock')
def test_use_mount(aggregator, instance_basic_mount, gauge_metrics, rate_metrics, count_metrics):
    """
    Same as above, using mount to tag
    """
    c = Disk('disk', {}, [instance_basic_mount])
    c.check(instance_basic_mount)

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(
            name,
            value=value,
            tags=['device:{}'.format(DEFAULT_MOUNT_POINT), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
        )

    for name, value in chain(iteritems(rate_metrics), iteritems(count_metrics)):
        aggregator.assert_metric(
            name,
            value=value,
            tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
        )

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks', 'timeout_mock')
def test_device_tagging(aggregator, gauge_metrics, rate_metrics, count_metrics):
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
        c.check(instance)

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

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=tags)

    for name, value in chain(iteritems(rate_metrics), iteritems(count_metrics)):
        aggregator.assert_metric(
            name,
            value=value,
            tags=[
                'device:{}'.format(DEFAULT_DEVICE_NAME),
                'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
                'optional:tags1',
                'label:mylab',
                'device_label:mylab',
            ],
        )

    aggregator.assert_all_metrics_covered()


def test_get_devices_label():
    c = Disk('disk', {}, [{}])

    with mock.patch(
        "datadog_checks.disk.disk.get_subprocess_output",
        return_value=mock_blkid_output(),
        __name__='get_subprocess_output',
    ):
        labels = c._get_devices_label()
        assert labels.get("/dev/mapper/vagrant--vg-root") == ["label:DATA", "device_label:DATA"]


@pytest.mark.usefixtures('psutil_mocks')
def test_min_disk_size(aggregator, gauge_metrics, rate_metrics, count_metrics):
    instance = {'min_disk_size': 0.001}
    c = Disk('disk', {}, [instance])

    m = MockDiskMetrics()
    m.total = 0
    with mock.patch('psutil.disk_usage', return_value=m, __name__='disk_usage'):
        c.check(instance)

    for name in gauge_metrics:
        aggregator.assert_metric(name, count=0)

    for name in rate_metrics:
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    for name in count_metrics:
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_labels_from_blkid_cache_file(
    aggregator, instance_blkid_cache_file, gauge_metrics, rate_metrics, count_metrics
):
    """
    Verify that the disk labels are set when the blkid_cache_file option is set
    """
    c = Disk('disk', {}, [instance_blkid_cache_file])
    c.check(instance_blkid_cache_file)
    for metric in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric(
            metric, tags=['device:/dev/sda1', 'device_name:sda1', 'label:MYLABEL', 'device_label:MYLABEL']
        )


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_blkid_cache_file_contains_no_labels(
    aggregator, instance_blkid_cache_file_no_label, gauge_metrics, rate_metrics, count_metrics
):
    """
    Verify that the disk labels are ignored if the cache file doesn't contain any
    """
    c = Disk('disk', {}, [instance_blkid_cache_file_no_label])
    c.check(instance_blkid_cache_file_no_label)
    for metric in chain(gauge_metrics, rate_metrics, count_metrics):
        aggregator.assert_metric(metric, tags=['device:/dev/sda1', 'device_name:sda1'])


@pytest.mark.usefixtures('psutil_mocks')
def test_timeout_config(aggregator):
    """Test timeout configuration value is used on every timeout on the check."""

    # Arbitrary value
    TIMEOUT_VALUE = 42
    instance = {'timeout': TIMEOUT_VALUE}
    c = Disk('disk', {}, [instance])

    # Mock timeout version
    def no_timeout(fun):
        return lambda *args: fun(args)

    with mock.patch('psutil.disk_partitions', return_value=[MockPart()]), mock.patch(
        'datadog_checks.disk.disk.timeout', return_value=no_timeout
    ) as mock_timeout:
        c.check(instance)

    mock_timeout.assert_called_with(TIMEOUT_VALUE)


@pytest.mark.usefixtures('psutil_mocks')
def test_timeout_warning(aggregator, gauge_metrics, rate_metrics, count_metrics):
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

    with mock.patch('psutil.disk_partitions', return_value=[MockPart(), MockPart(mountpoint="/faulty")]), mock.patch(
        'psutil.disk_usage', return_value=m, __name__='disk_usage'
    ), mock.patch('datadog_checks.disk.disk.timeout', return_value=faulty_timeout):
        c.check({})

    # Check that the warning is called once for the faulty disk
    c.log.warning.assert_called_once()

    for name in gauge_metrics:
        aggregator.assert_metric(name, count=0)

    for name in chain(rate_metrics, count_metrics):
        aggregator.assert_metric_has_tag(name, 'device:{}'.format(DEFAULT_DEVICE_NAME))
        aggregator.assert_metric_has_tag(name, 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME))

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks')
def test_include_all_devices(aggregator, gauge_metrics, rate_metrics):
    c = Disk('disk', {}, [{}])

    with mock.patch('psutil.disk_partitions', return_value=[]) as m:
        c.check({})
        # By default, we include all devices
        m.assert_called_with(all=True)

    instance = {'include_all_devices': False}
    c = Disk('disk', {}, [instance])

    with mock.patch('psutil.disk_partitions', return_value=[]) as m:
        c.check({})
        m.assert_called_with(all=False)
