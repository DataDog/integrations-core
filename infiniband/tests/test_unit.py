# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.infiniband import InfinibandCheck

from .common import (
    MOCK_DEVICE,
    MOCK_IB_COUNTER_DATA,
    MOCK_IB_UNSCALED_COUNTER_DATA,
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


def _base_tags():
    return [
        'device:' + MOCK_DEVICE,
        'port:' + MOCK_PORT,
        'link_layer:infiniband',
        'netdev:ens5f0',
        'gid_type:roce_v2',
        'firmware_version:16.35.4030',
        'hca_type:mt4129',
        'board_id:mt_0000000438',
        'node_type:ca',
        'custom:tag',
    ]


def test_check(aggregator, instance, mock_fs):
    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = _base_tags()

    _assert_metrics(aggregator, MOCK_IB_UNSCALED_COUNTER_DATA, 'infiniband', tags)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags)
    aggregator.assert_metric(
        'infiniband.port.rate',
        metric_type=aggregator.GAUGE,
        value=100_000_000_000,
        tags=tags,
        count=1,
    )

    # Status tags are normalized (lowercased, non-alphanumerics to underscores), so
    # "4: ACTIVE" yields port_state:active and "5: LinkUp" yields port_phys_state:linkup.
    for status_name, expected_state in (('state', 'active'), ('phys_state', 'linkup')):
        value = int(MOCK_STATUS_DATA[status_name].split(':', 1)[0].strip())

        expected_tags = tags + [f'port_{status_name}:{expected_state}']
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

    tags = _base_tags()

    _assert_metrics(aggregator, MOCK_IB_UNSCALED_COUNTER_DATA, 'infiniband', tags, count=count, m_type=m_type)
    _assert_metrics(aggregator, MOCK_RDMA_COUNTER_DATA, 'infiniband.rdma', tags, count=count, m_type=m_type)
    aggregator.assert_metric(
        'infiniband.port.rate',
        metric_type=aggregator.GAUGE,
        value=100_000_000_000,
        tags=tags,
        count=1,
    )


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


def test_data_counters_are_scaled_to_bytes(aggregator, instance, mock_fs):
    # IBTA defines PortRcvData/PortXmitData in units of 4-byte words, and the kernel applies
    # the >> 2 itself (mlx5 pma_cnt_ext_assign). metadata.csv declares these metrics in bytes,
    # so the raw sysfs value has to be multiplied by 4. The divisor is a fixed 4 per spec,
    # independent of link width, so this is not a per-device calculation.
    # Mock values are port_rcv_data=1000 and port_xmit_data=2000.
    instance = {'tags': ['custom:tag'], 'collection_type': 'both'}
    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    tags = _base_tags()
    aggregator.assert_metric('infiniband.port_rcv_data', value=4000, tags=tags, count=1)
    aggregator.assert_metric('infiniband.port_xmit_data', value=8000, tags=tags, count=1)
    # The scaling is applied once before submission, so both flavours carry it.
    aggregator.assert_metric('infiniband.port_rcv_data.count', value=4000, tags=tags, count=1)
    aggregator.assert_metric('infiniband.port_xmit_data.count', value=8000, tags=tags, count=1)


def test_phys_state_tag_is_normalized(aggregator, instance, mock_fs):
    # The kernel's phys_state table holds CamelCase names, one value with an internal space
    # ("Phy Test"), and "<unknown>" for index 0 or any out-of-range value. Emitting the raw
    # string produces a malformed tag value, and never matches a monitor filtering on
    # snake_case -- which is why the shipped physical_state monitor cannot fire on
    # link_error_recovery. Status tags must go through _normalize_tag_value like every other
    # tag this check emits.
    with mock.patch.dict(MOCK_STATUS_DATA, {'phys_state': '7: Phy Test'}):
        check = InfinibandCheck('infiniband', {}, [instance])
        check.check({})

    expected_tags = _base_tags() + ['port_phys_state:phy_test']
    aggregator.assert_metric('infiniband.port_phys_state', value=7, tags=expected_tags, count=1)


def test_configured_counters_absent_from_sysfs_are_logged(aggregator, instance, caplog, mock_fs):
    # Under glob-and-filter a wrong counter name produces no error, no warning and no metric
    # -- it is indistinguishable from a counter the hardware does not expose. That is how ~23
    # names which can never match a kernel file survived in the shipped allowlists. Logging
    # the difference makes the next round of drift visible instead of silent.
    # The mock exposes 4 of the configured counters, so symbol_error is absent by construction.
    check = InfinibandCheck('infiniband', {}, [instance])
    check.check({})

    assert "configured but not found" in caplog.text
    assert "symbol_error" in caplog.text


def test_check_skipped_when_gpu_monitoring_disabled(instance, mock_fs):
    # The check ships as part of the GPU monitoring SKU. With gpu.enabled off the instance
    # must be skipped outright rather than collecting a partial set of metrics.
    # mock_fs makes the sysfs path resolve so that the gate is the only reason to raise.
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            InfinibandCheck('infiniband', {}, [instance])
