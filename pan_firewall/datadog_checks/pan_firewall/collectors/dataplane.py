# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dataplane CPU per core, from `show running resource-monitor minute last 1`."""

from __future__ import annotations

from collections.abc import Callable
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from .base import CollectContext, Sample

RESOURCE_MONITOR_CMD = (
    '<show><running><resource-monitor><minute><last>1</last></minute></resource-monitor></running></show>'
)


def parse_dataplane(root: Element, warn: Callable[..., None]) -> list[Sample]:
    processors = root.find('result/resource-monitor/data-processors')
    if processors is None:
        warn('the resource monitor has no data processors: no dataplane CPU is reported')
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


def collect_dataplane(ctx: CollectContext) -> list[Sample]:
    return parse_dataplane(ctx.client.op(RESOURCE_MONITOR_CMD), ctx.warning)
