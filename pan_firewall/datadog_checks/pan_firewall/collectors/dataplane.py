# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dataplane CPU per core, from `show running resource-monitor minute last 1`."""

from __future__ import annotations

from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from . import CollectContext, Sample, once_log, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

RESOURCE_MONITOR_CMD = (
    '<show><running><resource-monitor><minute><last>1</last></minute></resource-monitor></running></show>'
)


def parse_dataplane(root: Element, log: CheckLoggingAdapter) -> list[Sample]:
    """One `dataplane.cpu.utilization` per data processor and core: the first value of the minute series."""
    processors = root.find('result/resource-monitor/data-processors')
    if processors is None:
        log.warning('the resource monitor has no data processors: no dataplane CPU is reported')
        return []
    samples = []
    for dp in processors:
        for entry in dp.findall('minute/cpu-load-average/entry'):
            core = text(entry, 'coreid')
            # With `last N`, the value is a comma-separated series, newest first.
            series = text(entry, 'value')
            value = _to_float(series.split(',')[0]) if series else None
            if core is None or value is None:
                continue
            samples.append(Sample('dataplane.cpu.utilization', value, (f'dp:{dp.tag}', f'core:{core}'), 'gauge'))
    return samples


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


@register('dataplane')
def collect_dataplane(ctx: CollectContext) -> list[Sample]:
    return parse_dataplane(ctx.client.op(RESOURCE_MONITOR_CMD), once_log(ctx))
