# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS
from datadog_checks.pan_firewall.collectors.dataplane import RESOURCE_MONITOR_CMD, parse_dataplane
from datadog_checks.pan_firewall.collectors.system import (
    DISK_SPACE_CMD,
    SYSTEM_RESOURCES_CMD,
    parse_disk,
    parse_system_resources,
)
from datadog_checks.pan_firewall.constants import COLLECTORS
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES, FW_A_TAGS, SYNTHETIC
from ..fixture_map import op_fixture
from ..helpers import new_check

MIB = 1024**2

CPU_STATES = ('user', 'system', 'nice', 'idle', 'iowait', 'hardirq', 'softirq', 'steal')


def load(path):
    return parse_response(path.read_bytes())


def by_name(samples):
    """Samples keyed by (name, tags); fails on a duplicate, which would be two values for one series."""
    result = {(s.name, s.tags): s.value for s in samples}
    assert len(result) == len(samples)
    return result


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
FW_B_SYSTEM = expected_system(
    (8.1, 4.8, 0.0, 85.5, 0.0, 1.6, 0.0, 0.0),
    (15734.7 * MIB, 381.0 * MIB, 4837.9 * MIB, 10515.9 * MIB),
    (4000.0 * MIB, 3998.7 * MIB, 1.2 * MIB),
    5155.8 * MIB,
)


def system_values(samples):
    values = by_name(samples)
    assert all(tags == () for _, tags in values)
    return {name: value for (name, _), value in values.items()}


@pytest.mark.parametrize(
    'firewall, expected',
    [pytest.param('fw-a', FW_A_SYSTEM, id='fw-a'), pytest.param('fw-b', FW_B_SYSTEM, id='fw-b')],
)
def test_system_resources_of_the_captures(firewall, expected):
    samples = parse_system_resources(load(FIXTURES / firewall / 'system_resources.xml'), mock.Mock())

    assert system_values(samples) == pytest.approx(expected)
    assert 'mgmt.swap.cached' not in {s.name for s in samples}
    assert {s.kind for s in samples} == {'gauge'}


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
    samples = parse_system_resources(load(SYNTHETIC / name), mock.Mock())

    assert system_values(samples) == pytest.approx(expected)


def test_missing_cpu_line_gives_memory_only_and_a_warning():
    log = mock.Mock()

    samples = parse_system_resources(load(SYNTHETIC / 'system_resources_no_cpu.xml'), log)

    names = {s.name for s in samples}
    assert names == {n for n in FW_A_SYSTEM if not n.startswith('mgmt.cpu.')}
    log.warning.assert_called_once()


@pytest.mark.parametrize(
    'body',
    [
        pytest.param('', id='empty'),
        pytest.param('not the top output at all', id='unknown-shape'),
    ],
)
def test_unknown_system_resources_shape_gives_no_samples_and_one_warning(body):
    root = parse_response(f'<response status="success"><result>{body}</result></response>'.encode())
    log = mock.Mock()

    assert parse_system_resources(root, log) == []
    log.warning.assert_called_once()


def test_dataplane_one_sample_per_dp_and_core_with_the_first_value():
    samples = parse_dataplane(load(SYNTHETIC / 'resource_monitor_two_dp_series.xml'), mock.Mock())

    assert by_name(samples) == {
        ('dataplane.cpu.utilization', ('dp:dp0', 'core:0')): 7,
        ('dataplane.cpu.utilization', ('dp:dp0', 'core:1')): 0,
        ('dataplane.cpu.utilization', ('dp:dp1', 'core:0')): 31,
        ('dataplane.cpu.utilization', ('dp:dp1', 'core:1')): 12,
    }
    assert {s.kind for s in samples} == {'gauge'}


def test_dataplane_of_the_capture():
    samples = parse_dataplane(load(op_fixture(RESOURCE_MONITOR_CMD)), mock.Mock())

    # The lab firewall has one data processor with 4 idle cores.
    assert by_name(samples) == {('dataplane.cpu.utilization', ('dp:dp0', f'core:{core}')): 0 for core in range(4)}


def test_dataplane_without_data_processors_gives_no_samples_and_one_warning():
    log = mock.Mock()

    assert parse_dataplane(load(SYNTHETIC / 'resource_monitor_no_dp.xml'), log) == []
    log.warning.assert_called_once()


def test_disk_of_the_capture_skips_virtual_filesystems():
    samples = parse_disk(load(op_fixture(DISK_SPACE_CMD)), mock.Mock())

    assert by_name(samples) == {
        ('disk.used_pct', ('mount:/', 'filesystem:/dev/root')): 43,
        ('disk.used_pct', ('mount:/opt/pancfg', 'filesystem:/dev/nvme0n1p5')): 32,
        ('disk.used_pct', ('mount:/opt/panrepo', 'filesystem:/dev/nvme0n1p6')): 30,
        ('disk.used_pct', ('mount:/opt/panlogs', 'filesystem:/dev/nvme0n1p8')): 1,
    }
    assert {s.kind for s in samples} == {'gauge'}


def test_disk_row_wrapped_onto_two_lines():
    samples = parse_disk(load(SYNTHETIC / 'disk_space_wrapped.xml'), mock.Mock())

    assert by_name(samples) == {
        ('disk.used_pct', ('mount:/', 'filesystem:/dev/root')): 43,
        ('disk.used_pct', ('mount:/opt/panlogs', 'filesystem:/dev/mapper/pan-very-long-volume-name')): 1,
    }


def test_collectors_are_registered_and_send_the_captured_commands(real_collectors):
    assert {'system_resources', 'dataplane', 'disk'} <= set(COLLECT_FUNCTIONS) <= set(COLLECTORS)
    for cmd in (SYSTEM_RESOURCES_CMD, RESOURCE_MONITOR_CMD, DISK_SPACE_CMD):
        assert op_fixture(cmd).is_file()


def test_collectors_submit_through_the_check(real_collectors, dd_run_check, aggregator):
    check = new_check()

    dd_run_check(check)

    def tags(*extra):
        return sorted([*FW_A_TAGS, *extra])

    for name, value in FW_A_SYSTEM.items():
        aggregator.assert_metric(f'pan_firewall.{name}', value, tags=FW_A_TAGS, metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'pan_firewall.dataplane.cpu.utilization', 0, tags=tags('dp:dp0', 'core:2'), metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        'pan_firewall.disk.used_pct',
        32,
        tags=tags('mount:/opt/pancfg', 'filesystem:/dev/nvme0n1p5'),
        metric_type=aggregator.GAUGE,
    )
    assert len(aggregator.metrics('pan_firewall.dataplane.cpu.utilization')) == 4
    assert len(aggregator.metrics('pan_firewall.disk.used_pct')) == 4
