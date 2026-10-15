# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Global counters (`show counter global`): the 26 `counter.global` series and `dropped_packets` by aspect."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.constants import DROPPED_PACKET_ASPECTS, GLOBAL_COUNTERS
from datadog_checks.pan_firewall.xml_utils import num, text

from .base import CollectContext, Sample, register

# Never a filter: `value all` answers with 5,524 counters.
GLOBAL_COUNTER_CMD = '<show><counter><global/></counter></show>'


def parse_global(root: Element) -> list[Sample] | None:
    """None when the response has no counters list. `counter.global` is sent for exactly `GLOBAL_COUNTERS`, an
    unlisted one as 0; `dropped_packets` sums the `severity=drop` counters by aspect."""
    counters = root.find('result/global/counters')
    if counters is None:
        return None
    listed: dict[str, tuple[float, str | None, str | None]] = {}
    drops: dict[str, float] = dict.fromkeys(DROPPED_PACKET_ASPECTS, 0)
    for entry in counters.iterfind('entry'):
        name = text(entry, 'name')
        value = num(entry, 'value')
        if not name or value is None:
            continue
        aspect = text(entry, 'aspect')
        listed[name] = (value, text(entry, 'category'), aspect)
        if text(entry, 'severity') == 'drop' and aspect:
            drops[aspect] = drops.get(aspect, 0) + value

    samples = []
    for name, (category, aspect) in GLOBAL_COUNTERS.items():
        value, listed_category, listed_aspect = listed.get(name, (0, None, None))
        tags = (f'counter:{name}', f'category:{listed_category or category}', f'aspect:{listed_aspect or aspect}')
        samples.append(Sample('counter.global', value, tags, 'monotonic_count'))
    samples.extend(
        Sample('dropped_packets', total, (f'aspect:{aspect}',), 'monotonic_count') for aspect, total in drops.items()
    )
    return samples


@register('global_counters')
def collect_global_counters(ctx: CollectContext) -> list[Sample]:
    samples = parse_global(ctx.client.op(GLOBAL_COUNTER_CMD))
    if samples is None:
        ctx.warning('`show counter global` has no counters list: no global counter is reported', key='global_counters')
        return []
    return samples
