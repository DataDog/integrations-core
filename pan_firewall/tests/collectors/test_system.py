# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.dataplane import RESOURCE_MONITOR_CMD, parse_dataplane
from datadog_checks.pan_firewall.collectors.system import (
    DISK_SPACE_CMD,
    SYSTEM_RESOURCES_CMD,
    parse_disk,
    parse_system_resources,
)

from ..common import MIB, SYNTHETIC
from ..helpers import load_op, load_xml, series

CPU_STATES = ('user', 'system', 'nice', 'idle', 'iowait', 'hardirq', 'softirq', 'steal')


def expected_system(cpu, mem, swap, avail):
    """`cpu` is the 8 states in top order; `mem` is (total, free, used, buff_cache), `swap` is (total, free, used)."""
    expected = {f'mgmt.cpu.{state}': value for state, value in zip(CPU_STATES, cpu)}
    expected['mgmt.cpu.used'] = 100 - cpu[3]
    expected.update(
        {
            'mgmt.memory.total': mem[0],
            'mgmt.memory.free': mem[1],
            'mgmt.memory.used': mem[2],
            'mgmt.memory.buff_cache': mem[3],
            'mgmt.memory.available': avail,
            'mgmt.memory.used_pct': mem[2] / mem[0] * 100,
            'mgmt.swap.total': swap[0],
            'mgmt.swap.free': swap[1],
            'mgmt.swap.used': swap[2],
            'mgmt.swap.used_pct': swap[2] / swap[0] * 100,
        }
    )
    return expected


FW_A_SYSTEM = expected_system(
    (8.2, 4.9, 0.0, 85.2, 0.0, 1.6, 0.0, 0.0),
    (15734.7 * MIB, 372.1 * MIB, 4804.7 * MIB, 10557.9 * MIB),
    (4000.0 * MIB, 3998.7 * MIB, 1.2 * MIB),
    5093.7 * MIB,
)


def system_values(samples):
    values = series(samples)
    assert all(tags == () and kind == 'gauge' for (_, tags), (_, kind) in values.items())
    return {name: value for (name, _), (value, _) in values.items()}


def test_system_resources_of_the_capture():
    samples = parse_system_resources(load_op(SYSTEM_RESOURCES_CMD), mock.Mock())

    assert system_values(samples) == pytest.approx(FW_A_SYSTEM)


GIB = 1024**3
KIB = 1024
UNIT_VARIANTS = [
    pytest.param(
        'system_resources_kib.xml',
        expected_system(
            (8.2, 4.9, 0.0, 85.2, 0.0, 1.6, 0.0, 0.0),
            (16112333 * KIB, 381030 * KIB, 4920013 * KIB, 10811290 * KIB),
            (4096000 * KIB, 4094669 * KIB, 1229 * KIB),
            5215949 * KIB,
        ),
        id='KiB',
    ),
    pytest.param(
        'system_resources_gib.xml',
        expected_system(
            (8.2, 4.9, 0.0, 85.2, 0.0, 1.6, 0.0, 0.0),
            (15.4 * GIB, 0.4 * GIB, 4.7 * GIB, 10.3 * GIB),
            (3.9 * GIB, 3.9 * GIB, 0.0),
            5.0 * GIB,
        ),
        id='GiB',
    ),
]


@pytest.mark.parametrize('name, expected', UNIT_VARIANTS)
def test_memory_unit_is_read_from_the_line_header(name, expected):
    samples = parse_system_resources(load_xml(SYNTHETIC / name), mock.Mock())

    assert system_values(samples) == pytest.approx(expected)


def test_missing_cpu_line_gives_memory_only_and_a_warning():
    warn = mock.Mock()

    samples = parse_system_resources(load_xml(SYNTHETIC / 'system_resources_no_cpu.xml'), warn)

    names = {s.name for s in samples}
    assert names == {n for n in FW_A_SYSTEM if not n.startswith('mgmt.cpu.')}
    warn.assert_called_once()


def test_dataplane_one_sample_per_dp_and_core_with_the_first_value():
    samples = parse_dataplane(load_xml(SYNTHETIC / 'resource_monitor_two_dp_series.xml'), mock.Mock())

    assert series(samples) == {
        ('dataplane.cpu.utilization', ('dp:dp0', 'core:0')): (7, 'gauge'),
        ('dataplane.cpu.utilization', ('dp:dp0', 'core:1')): (0, 'gauge'),
        ('dataplane.cpu.utilization', ('dp:dp1', 'core:0')): (31, 'gauge'),
        ('dataplane.cpu.utilization', ('dp:dp1', 'core:1')): (12, 'gauge'),
    }


def test_dataplane_of_the_capture():
    samples = parse_dataplane(load_op(RESOURCE_MONITOR_CMD), mock.Mock())

    # The lab firewall has one data processor with 4 idle cores.
    assert series(samples) == {
        ('dataplane.cpu.utilization', ('dp:dp0', f'core:{core}')): (0, 'gauge') for core in range(4)
    }


def test_dataplane_without_data_processors_gives_no_samples_and_one_warning():
    warn = mock.Mock()

    assert parse_dataplane(load_xml(SYNTHETIC / 'resource_monitor_no_dp.xml'), warn) == []
    warn.assert_called_once()


def test_disk_of_the_capture_skips_virtual_filesystems():
    samples = parse_disk(load_op(DISK_SPACE_CMD), mock.Mock())

    assert series(samples) == {
        ('disk.used_pct', ('mount:/', 'filesystem:/dev/root')): (43, 'gauge'),
        ('disk.used_pct', ('mount:/opt/pancfg', 'filesystem:/dev/nvme0n1p5')): (32, 'gauge'),
        ('disk.used_pct', ('mount:/opt/panrepo', 'filesystem:/dev/nvme0n1p6')): (30, 'gauge'),
        ('disk.used_pct', ('mount:/opt/panlogs', 'filesystem:/dev/nvme0n1p8')): (1, 'gauge'),
    }


def test_disk_row_wrapped_onto_two_lines():
    samples = parse_disk(load_xml(SYNTHETIC / 'disk_space_wrapped.xml'), mock.Mock())

    assert series(samples) == {
        ('disk.used_pct', ('mount:/', 'filesystem:/dev/root')): (43, 'gauge'),
        ('disk.used_pct', ('mount:/opt/panlogs', 'filesystem:/dev/mapper/pan-very-long-volume-name')): (1, 'gauge'),
    }
