# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Management-plane resources (`show system resources`) and filesystem usage (`show system disk-space`).

Both commands answer with the output of a Linux tool as text under `result`, so they are parsed by line.
The hardware sensors (`show system environmentals`) answer with XML.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import num, text

from . import CollectContext, Sample, once_log, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

SYSTEM_RESOURCES_CMD = '<show><system><resources/></system></show>'
DISK_SPACE_CMD = '<show><system><disk-space/></system></show>'
ENVIRONMENTALS_CMD = '<show><system><environmentals/></system></show>'

CPU_STATES = {'us': 'user', 'sy': 'system', 'ni': 'nice', 'id': 'idle'}
CPU_STATES |= {'wa': 'iowait', 'hi': 'hardirq', 'si': 'softirq', 'st': 'steal'}
# The unit top prints in the line header (`MiB Mem`, `KiB Swap`, ...).
UNIT_BYTES = {name: 1024**power for power, name in enumerate(('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'))}
# `top` line -> (metric group, (label, metric name) of each value the line must have).
MEMORY_LINES = {
    'Mem': ('memory', (('total', 'total'), ('free', 'free'), ('used', 'used'), ('buff/cache', 'buff_cache'))),
    'Swap': ('swap', (('total', 'total'), ('free', 'free'), ('used', 'used'))),
}
VIRTUAL_FILESYSTEMS = frozenset({'none', 'tmpfs', 'cgroup_root'})

ALARM_TRUE = frozenset({'true', 'yes'})
ALARM_FALSE = frozenset({'false', 'no'})

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
    for kind, (group, values) in MEMORY_LINES.items():
        line = lines.get(kind)
        fields = _fields(line['values']) if line else {}
        scale = UNIT_BYTES.get(line['unit']) if line else None
        if not scale or not {label for label, _ in values} <= fields.keys():
            missing.append(kind)
            continue
        samples.extend(Sample(f'mgmt.{group}.{name}', fields[label] * scale, (), 'gauge') for label, name in values)
        used_pct = _percent(fields['used'], fields['total'])
        if used_pct is not None:
            samples.append(Sample(f'mgmt.{group}.used_pct', used_pct, (), 'gauge'))
        # `avail Mem` is printed on the Swap line, in the unit of that line.
        if kind == 'Swap' and 'avail Mem' in fields:
            samples.append(Sample('mgmt.memory.available', fields['avail Mem'] * scale, (), 'gauge'))
    if missing:
        log.warning(
            '`show system resources` has no usable %s line: the metrics of the line are not reported',
            ', '.join(missing),
        )
    return samples


def parse_disk(root: Element, log: CheckLoggingAdapter) -> list[Sample]:
    """Parse `df` output: `disk.used_pct` per filesystem, without the virtual ones."""
    lines = (text(root, 'result') or '').splitlines()
    if not lines or not lines[0].startswith('Filesystem'):
        log.warning('`show system disk-space` is not df output: no disk usage is reported')
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


def _slot_number(slot: Element) -> str:
    """`Slot1` -> `1`; any other element name is used whole."""
    return slot.tag[4:] if slot.tag.lower().startswith('slot') and len(slot.tag) > 4 else slot.tag


def _entries(root: Element, section: str) -> Iterator[tuple[Element, str, str]]:
    """Yield (entry, slot number, sensor name) for `result/<section>/<slot>/entry`.

    The sensor is the entry's `description`; an entry without one is named after its slot element.
    """
    container = root.find(f'result/{section}')
    for slot in container if container is not None else ():
        for entry in slot.iterfind('entry'):
            yield entry, _slot_number(slot), text(entry, 'description') or slot.tag


def _alarm(entry: Element) -> bool | None:
    """PAN's `alarm` field as a bool, None when absent or not a recognised value."""
    value = (text(entry, 'alarm') or '').lower()
    if value in ALARM_TRUE:
        return True
    return False if value in ALARM_FALSE else None


def parse_environmentals(root: Element, log: CheckLoggingAdapter, warned: set[str]) -> list[Sample]:
    """Parse `show system environmentals`: power rails and temperature sensors.

    A VM-Series firewall answers with an empty `result`, so nothing is sent. The alarms are PAN's own `alarm` field,
    never a comparison of the reading with the thresholds. A power alarm whose direction cannot be told sends no alarm
    metric and logs one warning per sensor; `warned` holds the sensors already warned about for this firewall.
    """
    samples: list[Sample] = []
    for entry, slot, name in _entries(root, 'power'):
        tags = (f'sensor:{name}', f'slot:{slot}')
        volts = num(entry, 'Volts')
        if volts is None:
            continue
        low = num(entry, 'min')
        if low is None:
            low = num(entry, 'min-volt')
        high = num(entry, 'max')
        if high is None:
            high = num(entry, 'max-volt')
        samples.append(Sample('power.voltage', volts, tags, 'gauge'))
        if low is not None:
            samples.append(Sample('power.voltage.min', low, tags, 'gauge'))
        if high is not None:
            samples.append(Sample('power.voltage.max', high, tags, 'gauge'))
        alarm = _alarm(entry)
        if alarm is None:
            continue
        if not alarm:
            direction = (0, 0)
        elif high is not None and volts >= high:
            direction = (1, 0)
        elif low is not None and volts <= low:
            direction = (0, 1)
        else:
            key = f'power-sensor:{slot}/{name}'
            if key not in warned:
                warned.add(key)
                log.warning(
                    'power sensor `%s` (slot %s) is in alarm but the voltage is not outside its '
                    'thresholds: power.alarm.high and power.alarm.low are not reported for it',
                    name,
                    slot,
                )
            continue
        samples.append(Sample('power.alarm.high', direction[0], tags, 'gauge'))
        samples.append(Sample('power.alarm.low', direction[1], tags, 'gauge'))

    for entry, slot, name in _entries(root, 'thermal'):
        tags = (f'sensor:{name}', f'slot:{slot}')
        for metric, field in (
            ('temperature.current', 'DegreesC'),
            ('temperature.min', 'min'),
            ('temperature.max', 'max'),
        ):
            value = num(entry, field)
            if value is not None:
                samples.append(Sample(metric, value, tags, 'gauge'))
        alarm = _alarm(entry)
        if alarm is not None:
            samples.append(Sample('temperature.alarm', int(alarm), tags, 'gauge'))
    return samples


@register('system_resources')
def collect_system_resources(ctx: CollectContext) -> list[Sample]:
    return parse_system_resources(ctx.client.op(SYSTEM_RESOURCES_CMD), once_log(ctx))


@register('disk')
def collect_disk(ctx: CollectContext) -> list[Sample]:
    return parse_disk(ctx.client.op(DISK_SPACE_CMD), once_log(ctx))


@register('environment')
def collect_environment(ctx: CollectContext) -> list[Sample]:
    return parse_environmentals(ctx.client.op(ENVIRONMENTALS_CMD), ctx.log, ctx.state.warned)
