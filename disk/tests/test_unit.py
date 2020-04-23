# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from itertools import chain

import mock
import pytest
from six import iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.disk import Disk

from .common import DEFAULT_DEVICE_BASE_NAME, DEFAULT_DEVICE_NAME, DEFAULT_FILE_SYSTEM, DEFAULT_MOUNT_POINT
from .mocks import MockDiskMetrics, mock_blkid_output


def test_default_options():
    check = Disk('disk', {}, [{}])

    assert check._use_mount is False
    assert check._all_partitions is False
    assert check._file_system_whitelist is None
    assert check._file_system_blacklist == re.compile('iso9660$', re.I)
    assert check._device_whitelist is None
    assert check._device_blacklist is None
    assert check._mount_point_whitelist is None
    assert check._mount_point_blacklist is None
    assert check._tag_by_filesystem is False
    assert check._device_tag_re == []
    assert check._service_check_rw is False
    assert check._min_disk_size == 0


def test_bad_config():
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        Disk('disk', {}, [{}, {}])


@pytest.mark.usefixtures('psutil_mocks')
def test_default(aggregator, gauge_metrics, rate_metrics):
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
            aggregator.assert_metric(name, value=value, tags=tags)

        for name, value in iteritems(rate_metrics):
            aggregator.assert_metric(
                name,
                value=value,
                tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
            )

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks')
def test_rw(aggregator):
    """
    Check for 'ro' option in the mounts
    """
    instance = {'service_check_rw': 'yes', 'tag_by_label': False}
    c = Disk('disk', {}, [instance])
    c.check(instance)

    aggregator.assert_service_check('disk.read_write', status=Disk.CRITICAL)


@pytest.mark.usefixtures('psutil_mocks')
def test_use_mount(aggregator, instance_basic_mount, gauge_metrics, rate_metrics):
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

    for name, value in iteritems(rate_metrics):
        aggregator.assert_metric(
            name,
            value=value,
            tags=['device:{}'.format(DEFAULT_DEVICE_NAME), 'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME)],
        )

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('psutil_mocks')
def test_device_tagging(aggregator, gauge_metrics, rate_metrics):
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
        c.devices_label = {DEFAULT_DEVICE_NAME: 'label:mylab'}
        c.check(instance)

    # Assert metrics
    tags = [
        'type:dev',
        'tag:two',
        'device:{}'.format(DEFAULT_DEVICE_NAME),
        'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
        'optional:tags1',
        'label:mylab',
    ]

    for name, value in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value, tags=tags)

    for name, value in iteritems(rate_metrics):
        aggregator.assert_metric(
            name,
            value=value,
            tags=[
                'device:{}'.format(DEFAULT_DEVICE_NAME),
                'device_name:{}'.format(DEFAULT_DEVICE_BASE_NAME),
                'optional:tags1',
                'label:mylab',
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
        assert labels.get("/dev/mapper/vagrant--vg-root") == "label:DATA"


@pytest.mark.usefixtures('psutil_mocks')
def test_min_disk_size(aggregator, gauge_metrics, rate_metrics):
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

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_labels_from_blkid_cache_file(aggregator, instance_blkid_cache_file, gauge_metrics, rate_metrics):
    """
    Verify that the disk labels are set when the blkid_cache_file option is set
    """
    c = Disk('disk', {}, [instance_blkid_cache_file])
    c.check(instance_blkid_cache_file)
    for metric in chain(gauge_metrics, rate_metrics):
        aggregator.assert_metric(metric, tags=['device:/dev/sda1', 'device_name:sda1', 'label:MYLABEL'])


@pytest.mark.skipif(not Platform.is_linux(), reason='disk labels are only available on Linux')
@pytest.mark.usefixtures('psutil_mocks')
def test_blkid_cache_file_contains_no_labels(
    aggregator, instance_blkid_cache_file_no_label, gauge_metrics, rate_metrics
):
    """
    Verify that the disk labels are ignored if the cache file doesn't contain any
    """
    c = Disk('disk', {}, [instance_blkid_cache_file_no_label])
    c.check(instance_blkid_cache_file_no_label)
    for metric in chain(gauge_metrics, rate_metrics):
        aggregator.assert_metric(metric, tags=['device:/dev/sda1', 'device_name:sda1'])
