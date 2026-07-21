# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import collections

import mock
import pytest

from datadog_checks.btrfs import BTRFS
from datadog_checks.btrfs.btrfs import (
    BTRFS_IOC_DEV_INFO,
    BTRFS_IOC_FS_INFO,
    BTRFS_IOC_SPACE_INFO,
    DATA,
    DUP,
    FLAGS_MAPPER,
    GLB_RSV,
    METADATA,
    MIXED,
    RAID0,
    RAID1,
    RAID5,
    RAID6,
    RAID10,
    SINGLE,
    SYSTEM,
    UNKNOWN,
    sized_array,
)

pytestmark = pytest.mark.unit

DEVICE_TUPLE = collections.namedtuple('device_tuple', 'device mountpoint fstype opts')


def get_partitions(specs):
    return [DEVICE_TUPLE(device=device, mountpoint=mountpoint, fstype=fstype, opts='') for device, mountpoint, fstype in specs]


def dev_info(used_bytes, total_bytes):
    info = [0] * 19
    info[17] = used_bytes
    info[18] = total_bytes
    return tuple(info)


def make_struct(size=0, unpack=None, unpack_from=None):
    struct_mock = mock.MagicMock()
    struct_mock.size = size
    if unpack is not None:
        struct_mock.unpack.side_effect = unpack
    if unpack_from is not None:
        struct_mock.unpack_from.side_effect = unpack_from
    return struct_mock


def test_flags_mapper_matches_every_documented_btrfs_block_group_flag():
    # Kills the core/NumberReplacer mutants at btrfs.py:36-64 that alter or duplicate a
    # FLAGS_MAPPER key (each would drop or overwrite an entry in the dict below).
    assert FLAGS_MAPPER == {
        1: (SINGLE, DATA),
        2: (SINGLE, SYSTEM),
        4: (SINGLE, METADATA),
        5: (SINGLE, MIXED),
        9: (RAID0, DATA),
        10: (RAID0, SYSTEM),
        12: (RAID0, METADATA),
        13: (RAID0, MIXED),
        17: (RAID1, DATA),
        18: (RAID1, SYSTEM),
        20: (RAID1, METADATA),
        21: (RAID1, MIXED),
        33: (DUP, DATA),
        34: (DUP, SYSTEM),
        36: (DUP, METADATA),
        37: (DUP, MIXED),
        65: (RAID10, DATA),
        66: (RAID10, SYSTEM),
        68: (RAID10, METADATA),
        69: (RAID10, MIXED),
        129: (RAID5, DATA),
        130: (RAID5, SYSTEM),
        132: (RAID5, METADATA),
        133: (RAID5, MIXED),
        257: (RAID6, DATA),
        258: (RAID6, SYSTEM),
        260: (RAID6, METADATA),
        261: (RAID6, MIXED),
        562949953421312: (SINGLE, GLB_RSV),
    }


def test_flags_mapper_defaults_unrecognized_flags_to_single_unknown():
    assert FLAGS_MAPPER[9999] == (SINGLE, UNKNOWN)


def test_ioctl_command_constants_match_kernel_definitions():
    # Kills the core/NumberReplacer mutants at btrfs.py:68-70 that alter the ioctl request codes.
    assert BTRFS_IOC_SPACE_INFO == 0xC0109414
    assert BTRFS_IOC_DEV_INFO == 0xD000941E
    assert BTRFS_IOC_FS_INFO == 0x8400941F


def test_sized_array_returns_zero_filled_unsigned_byte_array():
    # Kills the core/NumberReplacer mutant at btrfs.py:82 (itertools.repeat(0, ...) -> repeat(1, ...)).
    result = sized_array(4)
    assert list(result) == [0, 0, 0, 0]
    assert result.typecode == 'B'


def test_get_usage_buffer_size_uses_addition_not_bitwise_ops():
    # Kills core/ReplaceBinaryOperator_Add_BitOr and _Add_BitXor at btrfs.py:119. The chosen
    # sizes overlap bits so +, |, ^ all yield different buffer_size values (9 vs 7 vs 5),
    # which changes how many times the range() loop below unpacks THREE_LONGS_STRUCT.
    check = BTRFS('btrfs', {}, [{}])
    two = make_struct(size=3, unpack=[(0, 3)], unpack_from=[(0, 3)])
    three = make_struct(size=2, unpack_from=[(1, 100, 10), (2, 200, 20), (3, 300, 30)])

    with mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions'), mock.patch(
        'datadog_checks.btrfs.btrfs.fcntl.ioctl'
    ), mock.patch('datadog_checks.btrfs.btrfs.TWO_LONGS_STRUCT', two), mock.patch(
        'datadog_checks.btrfs.btrfs.THREE_LONGS_STRUCT', three
    ):
        usage = check.get_usage('/')

    assert usage == [(1, 100, 10), (2, 200, 20), (3, 300, 30)]


def test_get_usage_uses_zero_offsets_for_pack_and_unpack():
    # Kills the core/NumberReplacer mutants at btrfs.py:122 and :125 that change the offsets
    # (and the padding value) passed to TWO_LONGS_STRUCT.pack_into/.unpack_from.
    check = BTRFS('btrfs', {}, [{}])
    two = make_struct(size=2, unpack=[(0, 1)], unpack_from=[(0, 1)])
    three = make_struct(size=2, unpack_from=[(7, 70, 7)])

    with mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions'), mock.patch(
        'datadog_checks.btrfs.btrfs.fcntl.ioctl'
    ), mock.patch('datadog_checks.btrfs.btrfs.TWO_LONGS_STRUCT', two), mock.patch(
        'datadog_checks.btrfs.btrfs.THREE_LONGS_STRUCT', three
    ):
        check.get_usage('/')

    pack_into_args = two.pack_into.call_args.args
    assert pack_into_args[1:] == (0, 1, 0)
    assert two.unpack_from.call_args.args[1] == 0


def test_get_unallocated_space_bounded_by_max_device_id_not_num_devices():
    # Kills the core/NumberReplacer mutants at btrfs.py:140-141 that swap which fs_info index
    # feeds max_id vs num_devices: with far more "reported" devices than device ids to scan,
    # only max_id + 1 ids may ever be probed.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(1, 5)])  # max_id=1 (2 device ids), num_devices=5
    dev_struct = make_struct(unpack_from=[dev_info(100, 1000), dev_info(50, 600)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl'), mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        result = check.get_unallocated_space('/')

    assert result is None
    assert dev_struct.unpack_from.call_count == 2
    assert fs_struct.unpack_from.call_args.args[1] == 0


def test_get_unallocated_space_sums_bytes_using_zero_offsets():
    # Kills core/NumberReplacer at btrfs.py:134 (unallocated_bytes init 0 -> 1/-1), the offset
    # mutants at :149/:151, and the +/- swap on the running byte total at :153.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(1, 2)])  # max_id=1, num_devices=2: exactly 2 ids
    dev_struct = make_struct(unpack_from=[dev_info(100, 1000), dev_info(50, 600)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl'), mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        result = check.get_unallocated_space('/')

    assert result == 1450  # (1000 - 100) + (600 - 50)
    for index, call in enumerate(dev_struct.pack_into.call_args_list):
        assert call.args[1] == 0
        assert call.args[2] == index
        assert call.args[3:] == tuple([0] * 1421)
    assert [call.args[1] for call in dev_struct.unpack_from.call_args_list] == [0, 0]


def test_get_unallocated_space_stops_scanning_once_num_devices_hits_zero():
    # Kills the core comparison/arithmetic mutants at btrfs.py:144-145 (range(max_id + 1),
    # `if num_devices == 0: break`) by giving fewer real devices than the max device id, so
    # the loop must stop early instead of exhausting the full id range.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(3, 2)])  # max_id=3 (4 ids), only 2 real devices
    dev_struct = make_struct(unpack_from=[dev_info(10, 110), dev_info(20, 220)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl'), mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        result = check.get_unallocated_space('/')

    assert result == 300  # (110 - 10) + (220 - 20)
    assert dev_struct.unpack_from.call_count == 2


def test_get_unallocated_space_scans_exactly_max_id_plus_one_device_ids():
    # Kills core/ReplaceBinaryOperator_Add_LShift at btrfs.py:144 (range(max_id + 1) ->
    # range(max_id << 1)). num_devices is kept large enough that it never reaches 0, so the
    # range's upper bound alone determines the iteration count: the mutant would probe a 4th,
    # unmocked device id and blow up on the exhausted side_effect list.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(2, 100)])  # max_id=2 (3 ids), num_devices never hits 0
    dev_struct = make_struct(unpack_from=[dev_info(1, 2), dev_info(3, 4), dev_info(5, 6)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl'), mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        result = check.get_unallocated_space('/')

    assert dev_struct.unpack_from.call_count == 3
    assert result is None  # num_devices (100 - 3 = 97) never reaches 0, so the metric is skipped


def test_get_unallocated_space_decrements_num_devices_by_one_per_success():
    # Kills core/ReplaceBinaryOperator_Sub_RShift at btrfs.py:154 (num_devices - 1 -> >> 1).
    # With num_devices=3 the two operations diverge on the second iteration (2 - 1 = 1 vs
    # 2 >> 1 = 1, then 1 - 1 = 0 vs 1 >> 1 = 0 is a false match at n=2, so start at 3 instead),
    # causing the mutant to break one iteration early and skip the third device entirely.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(2, 3)])  # max_id=2 (3 ids), num_devices=3
    dev_struct = make_struct(unpack_from=[dev_info(1, 10), dev_info(1, 20), dev_info(1, 30)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl'), mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        result = check.get_unallocated_space('/')

    assert dev_struct.unpack_from.call_count == 3
    assert result == 57  # (10 - 1) + (20 - 1) + (30 - 1), all three devices counted


def test_get_unallocated_space_skips_device_on_ioerror():
    # Kills core/ExceptionReplacer at btrfs.py:156 (except IOError -> except CosmicRayTestingException):
    # a failing device's IOError must be swallowed, not propagated, and its bytes excluded.
    check = BTRFS('btrfs', {}, [{}])
    fs_struct = make_struct(unpack_from=[(1, 2)])  # max_id=1, num_devices=2
    dev_struct = make_struct(unpack_from=[dev_info(10, 110)])

    with mock.patch('datadog_checks.btrfs.btrfs.fcntl.ioctl') as mock_ioctl, mock.patch(
        'datadog_checks.btrfs.btrfs.BTRFS_FS_INFO_STRUCT', fs_struct
    ), mock.patch('datadog_checks.btrfs.btrfs.BTRFS_DEV_INFO_STRUCT', dev_struct):
        # 1st call is BTRFS_IOC_FS_INFO; the next two are BTRFS_IOC_DEV_INFO for each device id.
        mock_ioctl.side_effect = [None, None, IOError("device gone")]
        result = check.get_unallocated_space('/')

    assert result is None  # the second device's info could not be retrieved, so skip the metric
    assert dev_struct.unpack_from.call_count == 1


@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions')
def test_check_raises_when_no_partition_has_btrfs_fstype(mock_partitions):
    # Kills core/ReplaceAndWithOr at btrfs.py:168 and the len(...) </<=/-1 mutants at :171: a
    # non-btrfs, non-excluded partition must not satisfy the "and"-chained filter on its own.
    mock_partitions.return_value = get_partitions([('/dev/sda1', '/mnt/a', 'ext4')])
    check = BTRFS('btrfs', {}, [{}])

    with pytest.raises(Exception, match="No btrfs device found"):
        check.check({})


@mock.patch('datadog_checks.btrfs.btrfs.BTRFS.get_usage', return_value=[(1, 1000, 400)])
@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions')
def test_check_only_selects_partitions_with_exact_btrfs_fstype(mock_partitions, mock_get_usage, aggregator, dd_run_check):
    # Kills core/ReplaceComparisonOperator_Eq_LtE and _Eq_GtE at btrfs.py:168: fstype values on
    # both sides of the 'btrfs' string ordering must be excluded, only an exact match counted.
    mock_partitions.return_value = get_partitions(
        [
            ('/dev/alpha', '/mnt/alpha', 'alpha'),  # sorts before 'btrfs'
            ('/dev/zzzfs', '/mnt/zzzfs', 'zzzfs'),  # sorts after 'btrfs'
            ('/dev/real', '/mnt/real', 'btrfs'),
        ]
    )
    check = BTRFS('btrfs', {}, [{}])

    with mock.patch.object(check, 'get_unallocated_space', return_value=None):
        dd_run_check(check)

    aggregator.assert_metric('system.disk.btrfs.total', count=1)


@mock.patch('datadog_checks.btrfs.btrfs.BTRFS.get_usage', return_value=[(1, 1000, 400)])
@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions')
def test_check_free_and_usage_are_computed_from_total_and_used(mock_partitions, mock_get_usage, aggregator, dd_run_check):
    # Kills core/ReplaceBinaryOperator_Sub_* at btrfs.py:184 (free = total - used) and
    # core/ReplaceBinaryOperator_Div_* at btrfs.py:185 (usage = used / total).
    mock_partitions.return_value = get_partitions([('/dev/real', '/mnt/real', 'btrfs')])
    check = BTRFS('btrfs', {}, [{}])

    with mock.patch.object(check, 'get_unallocated_space', return_value=None):
        dd_run_check(check)

    aggregator.assert_metric('system.disk.btrfs.free', value=600)
    aggregator.assert_metric('system.disk.btrfs.usage', value=0.4)


@mock.patch('datadog_checks.btrfs.btrfs.BTRFS.get_usage', return_value=[(1, 1000, 400)])
@mock.patch('datadog_checks.btrfs.btrfs.psutil.disk_partitions')
def test_check_emits_unallocated_metric_when_value_is_present(mock_partitions, mock_get_usage, aggregator, dd_run_check):
    # Kills core/ReplaceComparisonOperator_IsNot_Is and core/AddNot at btrfs.py:193 (both flip
    # which branch a non-None unallocated_bytes takes), and every core/ReplaceBinaryOperator_Add_*
    # at btrfs.py:194: with a non-empty custom_tags list, `+` is the only operator two lists
    # support, so any other operator mutant raises TypeError instead of tagging the metric.
    mock_partitions.return_value = get_partitions([('/dev/real', '/mnt/real', 'btrfs')])
    check = BTRFS('btrfs', {}, [{'tags': ['custom:mytag']}])

    with mock.patch.object(check, 'get_unallocated_space', return_value=5000):
        dd_run_check(check)

    aggregator.assert_metric(
        'system.disk.btrfs.unallocated', value=5000, tags=['device:/dev/real', 'custom:mytag'], count=1
    )
