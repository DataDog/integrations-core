# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.infiniband import InfinibandCheck

from .common import (
    MOCK_DEVICE,
    MOCK_IB_COUNTER_DATA,
    MOCK_PORT,
    MOCK_RDMA_COUNTER_DATA,
    MOCK_STATUS_DATA,
)


def _assert_metrics(aggregator, metrics, metric_prefix, tags, count=1, m_type='gauge'):
    for counter, value in metrics.items():
        if m_type in {'gauge', 'both'}:
            aggregator.assert_metric(
                f'{metric_prefix}.{counter}',
                metric_type=aggregator.GAUGE,
                value=int(value),
                tags=tags,
                count=count,
            )

        if m_type in {'monotonic_count', 'both'}:
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

    for status_name, status_value in MOCK_STATUS_DATA.items():
        value, state_name = status_value.split(':', 1)
        value = int(value.strip())
        state_name = state_name.strip()

        expected_tags = tags + [f'port_{status_name}:{state_name}']
        aggregator.assert_metric(
            f'infiniband.port_{status_name}',
            metric_type=aggregator.GAUGE,
            value=value,
            tags=expected_tags,
            count=1,
        )


@pytest.mark.parametrize(
    "collection_type,m_type,count",
    [
        ('gauge', 'gauge', 1),
        ('monotonic_count', 'monotonic_count', 0),
        ('both', 'both', 1),
    ],
    ids=[
        'gauge collection_type',
        'monotonic_count collection_type',
        'both collection_type',
    ],
)
def test_collection_types(aggregator, mock_fs, collection_type, m_type, count):
    # Test different collection_type parameters
    instance = {'tags': ['custom:tag'], 'collection_type': collection_type}

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = ['device:' + MOCK_DEVICE, 'port:' + MOCK_PORT, 'custom:tag']

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', tags, count=count, m_type=m_type)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags, count=count, m_type=m_type)


def test_exclude_devices(aggregator, mock_fs):
    # Test exclude_devices parameter
    instance = {
        'exclude_devices': [MOCK_DEVICE],
        'tags': ['custom:tag'],
    }

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    _assert_metrics(aggregator, MOCK_IB_COUNTER_DATA, 'infiniband', [], count=0)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', [], count=0)


def test_exclude_counters(aggregator, mock_fs):
    # Test exclude_counters parameter
    excluded_counter = next(iter(MOCK_IB_COUNTER_DATA.keys()))
    instance = {
        'exclude_counters': [excluded_counter],
        'tags': ['custom:tag'],
    }

    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    aggregator.assert_metric(f'infiniband.{excluded_counter}', count=0)


def test_collection_type_invalid():
    # Test invalid collection_type parameter
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
    # Test invalid path
    with pytest.raises(expected_exception):
        check = InfinibandCheck('infiniband', {}, [test_instance])
        check.check({})


def test_device_without_ports_directory(aggregator, instance, caplog, mock_fs):
    # Test device without ports directory
    with mock.patch('os.path.isdir') as mock_isdir:
        mock_isdir.side_effect = lambda path: False if path.endswith('ports') else True

        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})

        assert "Skipping device mlx5_0 as it does not have a ports directory" in caplog.text

        assert len(aggregator._metrics) == 0


@pytest.mark.parametrize(
    "directory_type, expected_message",
    [
        ('counters', 'as counters directory does not exist'),
        ('hw_counters', 'as hw_counters directory does not exist'),
    ],
    ids=[
        'counters directory does not exist',
        'hw_counters directory does not exist',
    ],
)
def test_device_without_directories(aggregator, instance, caplog, mock_fs, directory_type, expected_message):
    # Test device without counters or hw_counters directories
    with mock.patch('os.path.isdir') as mock_isdir:

        def mock_isdir_fn(path):
            if path.endswith(directory_type):
                return False
            return True

        mock_isdir.side_effect = mock_isdir_fn

        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})

        assert "Skipping device" in caplog.text
        assert expected_message in caplog.text


def test_alternative_path(aggregator, instance, mock_fs):
    # Test alternative path
    with mock.patch('os.path.exists') as mock_exists:
        mock_exists.side_effect = lambda x: not x.startswith('/sys')

        check = InfinibandCheck('infiniband', {}, [instance])
        assert check.base_path.startswith('/host')
