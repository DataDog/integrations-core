# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Management-plane resources (`show system resources`) and filesystem usage (`show system disk-space`).

Both commands answer with the output of a Linux tool as text under `result`, so they are parsed by line.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from . import CollectContext, Sample, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

SYSTEM_RESOURCES_CMD = '<show><system><resources/></system></show>'
DISK_SPACE_CMD = '<show><system><disk-space/></system></show>'

CPU_STATES = {
    'us': 'user',
    'sy': 'system',
    'ni': 'nice',
    'id': 'idle',
    'wa': 'iowait',
    'hi': 'hardirq',
    'si': 'softirq',
    'st': 'steal',
}
# The unit top prints in the line header (`MiB Mem`, `KiB Swap`, ...).
UNIT_BYTES = {name: 1024**power for power, name in enumerate(('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'))}
# Filesystems that are not storage.
VIRTUAL_FILESYSTEMS = frozenset({'none', 'tmpfs', 'cgroup_root'})

CPU_LINE = re.compile(r'^%Cpu\(s\):(?P<values>.*)$', re.MULTILINE)
MEMORY_LINE = re.compile(r'^(?P<unit>\w+) (?P<kind>Mem|Swap)\s*:(?P<values>.*)$', re.MULTILINE)
VALUE = re.compile(r'(?P<number>\d+(?:\.\d+)?)\s+(?P<label>[a-zA-Z/]+(?: Mem)?)')


def _fields(line: str) -> dict[str, float]:
    return {m['label']: float(m['number']) for m in VALUE.finditer(line)}


def _percent(part: float, total: float) -> float | None:
    return part / total * 100 if total else None


def parse_system_resources(root: Element, log: CheckLoggingAdapter) -> list[Sample]:
    """Parse the `top` header of `show system resources`: CPU states, memory and swap.

    A line that is missing or in an unknown shape drops its own metrics; one warning names the lines dropped.
    """
    output = text(root, 'result') or ''
    samples: list[Sample] = []
    missing = []

    cpu = CPU_LINE.search(output)
    states = _fields(cpu['values']) if cpu else {}
    if CPU_STATES.keys() <= states.keys():
        samples.extend(Sample(f'mgmt.cpu.{name}', states[label], (), 'gauge') for label, name in CPU_STATES.items())
        samples.append(Sample('mgmt.cpu.used', 100 - states['id'], (), 'gauge'))
    else:
        missing.append('%Cpu(s)')

    lines = {m['kind']: m for m in MEMORY_LINE.finditer(output)}
    memory = _fields(lines['Mem']['values']) if 'Mem' in lines else {}
    mem_scale = UNIT_BYTES.get(lines['Mem']['unit']) if 'Mem' in lines else None
    if mem_scale and {'total', 'free', 'used', 'buff/cache'} <= memory.keys():
        for label, name in (('total', 'total'), ('free', 'free'), ('used', 'used'), ('buff/cache', 'buff_cache')):
            samples.append(Sample(f'mgmt.memory.{name}', memory[label] * mem_scale, (), 'gauge'))
        used_pct = _percent(memory['used'], memory['total'])
        if used_pct is not None:
            samples.append(Sample('mgmt.memory.used_pct', used_pct, (), 'gauge'))
    else:
        missing.append('Mem')

    swap = _fields(lines['Swap']['values']) if 'Swap' in lines else {}
    swap_scale = UNIT_BYTES.get(lines['Swap']['unit']) if 'Swap' in lines else None
    if swap_scale and {'total', 'free', 'used'} <= swap.keys():
        for name in ('total', 'free', 'used'):
            samples.append(Sample(f'mgmt.swap.{name}', swap[name] * swap_scale, (), 'gauge'))
        used_pct = _percent(swap['used'], swap['total'])
        if used_pct is not None:
            samples.append(Sample('mgmt.swap.used_pct', used_pct, (), 'gauge'))
        # `avail Mem` is printed on the Swap line, in the unit of that line.
        if 'avail Mem' in swap:
            samples.append(Sample('mgmt.memory.available', swap['avail Mem'] * swap_scale, (), 'gauge'))
    else:
        missing.append('Swap')
    if missing:
        log.warning(
            'pan_firewall: `show system resources` has no usable %s line: the metrics of the line are not reported',
            ', '.join(missing),
        )
    return samples


def parse_disk(root: Element, log: CheckLoggingAdapter) -> list[Sample]:
    """Parse `df` output: `disk.used_pct` per filesystem, without the virtual ones."""
    lines = (text(root, 'result') or '').splitlines()
    if not lines or not lines[0].startswith('Filesystem'):
        log.warning('pan_firewall: `show system disk-space` is not df output: no disk usage is reported')
        return []
    samples = []
    pending = ''
    for line in lines[1:]:
        # df wraps a row whose filesystem name is too long for its column onto the next line.
        row = (pending + ' ' + line).split(None, 5)
        pending = ''
        if len(row) == 1:
            pending = row[0]
            continue
        if len(row) < 6 or not row[4].endswith('%'):
            continue
        filesystem, _size, _used, _avail, use, mount = row
        if filesystem in VIRTUAL_FILESYSTEMS:
            continue
        try:
            value = float(use[:-1])
        except ValueError:
            continue
        samples.append(Sample('disk.used_pct', value, (f'mount:{mount}', f'filesystem:{filesystem}'), 'gauge'))
    return samples


@register('system_resources')
def collect_system_resources(ctx: CollectContext) -> list[Sample]:
    return parse_system_resources(ctx.client.op(SYSTEM_RESOURCES_CMD), ctx.log)


@register('disk')
def collect_disk(ctx: CollectContext) -> list[Sample]:
    return parse_disk(ctx.client.op(DISK_SPACE_CMD), ctx.log)
