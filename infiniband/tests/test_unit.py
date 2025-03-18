# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import mock

from datadog_checks.infiniband import InfinibandCheck

from .common import (
    MOCK_DEVICE,
    MOCK_IB_COUNTER_DATA,
    MOCK_PORT,
    MOCK_RDMA_COUNTER_DATA,
)


def _assert_metrics(aggregator, metrics, metric_prefix, tags, count=1, include_count=False):
    for counter, value in metrics.items():
        aggregator.assert_metric(
            f'{metric_prefix}.{counter}',
            metric_type=aggregator.GAUGE,
            value=int(value),
            tags=tags,
            count=count,
        )

        if include_count:
            aggregator.assert_metric(
                f'{metric_prefix}.{counter}.count',
                metric_type=aggregator.MONOTONIC_COUNT,
                value=int(value),
                tags=tags,
                count=1,
            )


def test_check(aggregator, instance, mock_fs):
    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = ['device:' + MOCK_DEVICE, 'port:' + MOCK_PORT, 'custom:tag']

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', tags)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags)


def test_collection_type_gauge(aggregator, mock_fs):
    """Test collection_type='gauge' (default)"""
    instance = {'tags': ['custom:tag'], 'collection_type': 'gauge'}

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = ['device:' + MOCK_DEVICE, 'port:' + MOCK_PORT, 'custom:tag']

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', tags)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags)


def test_collection_type_monotonic_count(aggregator, mock_fs):
    """Test collection_type='monotonic_count'"""
    instance = {'tags': ['custom:tag'], 'collection_type': 'monotonic_count'}

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = ['device:' + MOCK_DEVICE, 'port:' + MOCK_PORT, 'custom:tag']

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', tags, count=0)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags, count=0)

    for counter, value in MOCK_IB_COUNTER_DATA.items():
        aggregator.assert_metric(
            f'infiniband.{counter}.count',
            value=int(value),
            tags=tags,
            count=1,
        )

    for counter, value in MOCK_RDMA_COUNTER_DATA.items():
        aggregator.assert_metric(
            f'infiniband.rdma.{counter}.count',
            value=int(value),
            tags=tags,
            count=1,
        )


def test_collection_type_both(aggregator, mock_fs):
    """Test collection_type='both'"""
    instance = {'tags': ['custom:tag'], 'collection_type': 'both'}

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = ['device:' + MOCK_DEVICE, 'port:' + MOCK_PORT, 'custom:tag']

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', tags, include_count=True)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags, include_count=True)


def test_exclude_devices(aggregator, mock_fs):
    """Test exclude_devices functionality"""
    instance = {
        'exclude_devices': [MOCK_DEVICE],
        'tags': ['custom:tag'],
    }

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', [], count=0)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', [], count=0)


def test_exclude_counters(aggregator, mock_fs):
    """Test exclude_counters functionality"""
    excluded_counter = next(iter(MOCK_IB_COUNTER_DATA.keys()))
    instance = {
        'exclude_counters': [excluded_counter],
        'tags': ['custom:tag'],
    }

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    aggregator.assert_metric(f'infiniband.{excluded_counter}', count=0)


def test_collection_type_invalid():
    """Test invalid collection_type value"""
    instance = {'tags': ['custom:tag'], 'collection_type': 'invalid'}

    with pytest.raises(Exception, match="collection_type must be one of: 'gauge', 'monotonic_count', 'both'"):
        InfinibandCheck('infiniband', {}, [instance])


@pytest.mark.parametrize(
    "test_instance, expected_exception",
    [
        (
            {'infiniband_path': '/nonexistent/path'},
            Exception,
        ),
    ],
)
def test_config_errors(test_instance, expected_exception):
    """Test configuration error cases"""
    with pytest.raises(expected_exception):
        check = InfinibandCheck('infiniband', {}, [test_instance])
        check.check({})


def test_device_without_ports_directory(aggregator, instance, caplog, mock_fs):
    """Test device that doesn't have a ports directory"""
    with mock.patch('os.path.isdir') as mock_isdir:

        mock_isdir.side_effect = lambda path: False if path.endswith('ports') else True
        
        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})


        assert "Skipping device mlx5_0 as it does not have a ports directory" in caplog.text

        assert len(aggregator._metrics) == 0


def test_device_without_counters_directory(aggregator, instance, caplog, mock_fs):
    """Test device that doesn't have a counters directory"""
    with mock.patch('os.path.isdir') as mock_isdir:
        def mock_isdir_fn(path):
            if path.endswith('counters'):
                return False
            return True

        mock_isdir.side_effect = mock_isdir_fn
        
        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})


        assert "Skipping device" in caplog.text
        assert "as counters directory does not exist" in caplog.text


def test_device_without_hw_counters_directory(aggregator, instance, caplog, mock_fs):
    """Test device that doesn't have a hw_counters directory"""
    with mock.patch('os.path.isdir') as mock_isdir:
        def mock_isdir_fn(path):
            if path.endswith('hw_counters'):
                return False
            return True

        mock_isdir.side_effect = mock_isdir_fn
        
        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})


        assert "Skipping device" in caplog.text
        assert "as hw_counters directory does not exist" in caplog.text


def test_alternative_path(aggregator, instance, mock_fs):
    """Test the alternative path logic when base path doesn't exist"""
    with mock.patch('os.path.exists') as mock_exists:

        mock_exists.side_effect = lambda x: not x.startswith('/sys')
        
        check = InfinibandCheck('infiniband', {}, [instance])
        assert check.base_path.startswith('/host')
