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

pytestmark = pytest.mark.unit

KIB = 1024
GIB = 1024**3
# The `%Cpu(s)` line of the capture, which the synthetic answers keep, in top order.
CPU = {
    'user': 8.2,
    'system': 4.9,
    'nice': 0.0,
    'idle': 85.2,
    'iowait': 0.0,
    'hardirq': 1.6,
    'softirq': 0.0,
    'steal': 0.0,
}


def expected_system(mem, swap, available):
    """`mem` is (total, free, used, buff_cache) and `swap` is (total, free, used), in bytes."""
    return {
        **{f'mgmt.cpu.{state}': value for state, value in CPU.items()},
        'mgmt.cpu.used': 100 - CPU['idle'],
        **dict(zip(('mgmt.memory.total', 'mgmt.memory.free', 'mgmt.memory.used', 'mgmt.memory.buff_cache'), mem)),
        'mgmt.memory.available': available,
        'mgmt.memory.used_pct': mem[2] / mem[0] * 100,
        **dict(zip(('mgmt.swap.total', 'mgmt.swap.free', 'mgmt.swap.used'), swap)),
        'mgmt.swap.used_pct': swap[2] / swap[0] * 100,
    }


FW_A_SYSTEM = expected_system(
    (15734.7 * MIB, 372.1 * MIB, 4804.7 * MIB, 10557.9 * MIB), (4000.0 * MIB, 3998.7 * MIB, 1.2 * MIB), 5093.7 * MIB
)


def values(samples):
    return {name: value for (name, _tags), (value, _kind) in series(samples).items()}


@pytest.mark.parametrize(
    'root, expected',
    [
        pytest.param(load_op(SYSTEM_RESOURCES_CMD), FW_A_SYSTEM, id='MiB-capture'),
        pytest.param(
            load_xml(SYNTHETIC / 'system_resources_kib.xml'),
            expected_system(
                (16112333 * KIB, 381030 * KIB, 4920013 * KIB, 10811290 * KIB),
                (4096000 * KIB, 4094669 * KIB, 1229 * KIB),
                5215949 * KIB,
            ),
            id='KiB',
        ),
        pytest.param(
            load_xml(SYNTHETIC / 'system_resources_gib.xml'),
            expected_system((15.4 * GIB, 0.4 * GIB, 4.7 * GIB, 10.3 * GIB), (3.9 * GIB, 3.9 * GIB, 0.0), 5.0 * GIB),
            id='GiB',
        ),
    ],
)
def test_system_resources_in_the_unit_of_each_line(root, expected):
    assert values(parse_system_resources(root, mock.Mock())) == pytest.approx(expected)


def test_missing_cpu_line_gives_memory_only():
    samples = parse_system_resources(load_xml(SYNTHETIC / 'system_resources_no_cpu.xml'), mock.Mock())

    assert {s.name for s in samples} == {n for n in FW_A_SYSTEM if not n.startswith('mgmt.cpu.')}


@pytest.mark.parametrize(
    'root, utilization',
    [
        # The lab firewall has one data processor with 4 idle cores.
        pytest.param(
            load_op(RESOURCE_MONITOR_CMD), {('dp0', 0): 0, ('dp0', 1): 0, ('dp0', 2): 0, ('dp0', 3): 0}, id='capture'
        ),
        # Each core has a series of values, newest first: only the first is sent.
        pytest.param(
            load_xml(SYNTHETIC / 'resource_monitor_two_dp_series.xml'),
            {('dp0', 0): 7, ('dp0', 1): 0, ('dp1', 0): 31, ('dp1', 1): 12},
            id='two-data-processors',
        ),
    ],
)
def test_dataplane_cpu(root, utilization):
    assert series(parse_dataplane(root, mock.Mock())) == {
        ('dataplane.cpu.utilization', (f'dp:{dp}', f'core:{core}')): (value, 'gauge')
        for (dp, core), value in utilization.items()
    }


@pytest.mark.parametrize(
    'root, used_pct',
    [
        # Virtual filesystems (`none`, `tmpfs`, `cgroup_root`) are skipped.
        pytest.param(
            load_op(DISK_SPACE_CMD),
            {
                ('/', '/dev/root'): 43,
                ('/opt/pancfg', '/dev/nvme0n1p5'): 32,
                ('/opt/panrepo', '/dev/nvme0n1p6'): 30,
                ('/opt/panlogs', '/dev/nvme0n1p8'): 1,
            },
            id='capture',
        ),
        pytest.param(
            load_xml(SYNTHETIC / 'disk_space_wrapped.xml'),
            {('/', '/dev/root'): 43, ('/opt/panlogs', '/dev/mapper/pan-very-long-volume-name'): 1},
            id='row-wrapped-onto-two-lines',
        ),
    ],
)
def test_disk_used_pct(root, used_pct):
    assert series(parse_disk(root, mock.Mock())) == {
        ('disk.used_pct', (f'mount:{mount}', f'filesystem:{filesystem}')): (value, 'gauge')
        for (mount, filesystem), value in used_pct.items()
    }
