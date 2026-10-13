# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Interface counters (`show counter interface all`) and speeds (from the cached `show interface all`).

The one counters response also carries the `tunnel.N` rows. Those are the IPSec tunnel counters, tagged with what the
`vpn` collector stored in the state on an earlier run: the collectors run in parallel, so reading `vpn`'s result of the
same run would be a race. Until `vpn` first answers the tunnel counters are not sent: a series with fewer tags would
start a monotonic_count context that is dropped as soon as the full tags arrive.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.constants import NDM_INTERFACE_RESOURCE_TAG
from datadog_checks.pan_firewall.xml_utils import num, text

from . import CollectContext, FirewallState, Sample, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

COUNTER_INTERFACE_CMD = '<show><counter><interface>all</interface></counter></show>'

INTERFACE_METRICS = {
    'ibytes': 'interface.rx.bytes',
    'obytes': 'interface.tx.bytes',
    'ipackets': 'interface.rx.packets',
    'opackets': 'interface.tx.packets',
    'ierrors': 'interface.rx.errors',
    'idrops': 'interface.rx.drops',
    'ifwderrors': 'interface.forward_errors',
    'flowstate': 'interface.flow_state',
    'land': 'interface.attack.land',
    'pod': 'interface.attack.ping_of_death',
    'teardrop': 'interface.attack.teardrop',
    'ipspoof': 'interface.attack.ip_spoof',
    'macspoof': 'interface.attack.mac_spoof',
}
TUNNEL_METRICS = {
    'ibytes': 'ipsec.tunnel.rx.bytes',
    'obytes': 'ipsec.tunnel.tx.bytes',
    'ipackets': 'ipsec.tunnel.rx.packets',
    'opackets': 'ipsec.tunnel.tx.packets',
}
TUNNEL_INTERFACE = re.compile(r'^tunnel\.\d+$')
INTERFACE_KIND = re.compile(r'^[a-z]+')
# `hw/entry/speed` values that mean the speed is not known or does not apply.
NO_SPEED = frozenset({'ukn', '[n/a]'})
MEGABIT = 10**6


def _vsys(value: str | None) -> str | None:
    if not value:
        return None
    return value if value.startswith('vsys') else f'vsys{value}'


def interface_tags(name: str, state: FirewallState, serial: str | None) -> tuple[str, ...]:
    """The tags of an interface. Without the cached `show interface all` only `interface` is known."""
    tags = [f'interface:{name}']
    if state.interface_map is None:
        return tuple(tags)
    kind = INTERFACE_KIND.match(name)
    if kind:
        tags.append(f'interface_type:{kind.group()}')
    row = next((r for r in state.interface_rows if text(r, 'name') == name), None)
    if row is not None:
        forward = text(row, 'fwd') or ''
        values = (
            ('zone', text(row, 'zone')),
            ('vsys', _vsys(text(row, 'vsys'))),
            ('vr', forward[3:] if forward.startswith('vr:') else None),
        )
        tags.extend(f'{key}:{value}' for key, value in values if value)
    if serial:
        tags.append(f'{NDM_INTERFACE_RESOURCE_TAG}:{serial}')
    return tuple(tags)


def parse_interface_counters(
    root: Element,
    state: FirewallState,
    serial: str | None,
    tunnel_tags: dict[str, tuple[str, ...]] | None,
    log: CheckLoggingAdapter,
) -> list[Sample]:
    """Parse `counter interface all`: `interface.*` for each interface, `ipsec.tunnel.*` for each `tunnel.N` row.

    `tunnel_tags` is what `vpn` stored (None before it first answered, when no tunnel counters are sent). A `tunnel.N`
    row it does not list is not an IPSec tunnel and is not reported.
    """
    rows = root.findall('./result/ifnet/ifnet/entry')
    if not rows:
        log.warning('pan_firewall: `show counter interface all` has no interface rows: no interface counters are sent')
        return []
    samples: list[Sample] = []
    for row in rows:
        name = text(row, 'name')
        if not name:
            continue
        if TUNNEL_INTERFACE.match(name):
            # Without the tags a tunnel series would be a useless monotonic_count context: wait for `vpn`.
            metrics, kind_tags = TUNNEL_METRICS, (tunnel_tags or {}).get(name)
        else:
            metrics, kind_tags = INTERFACE_METRICS, interface_tags(name, state, serial)
        if kind_tags is None:
            continue
        for field_name, metric in metrics.items():
            value = num(row, field_name)
            if value is not None:
                samples.append(Sample(metric, value, kind_tags, 'monotonic_count'))
    return samples


def parse_interface_speeds(state: FirewallState, serial: str | None, log: CheckLoggingAdapter) -> list[Sample]:
    """`interface.speed` in bit/s from the cached `hw/entry/speed`, which PAN-OS gives in Mbps (L8 confirms)."""
    samples = []
    for name, entry in (state.interface_map or {}).items():
        raw = text(entry, 'speed')
        if raw is None or raw in NO_SPEED:
            continue
        try:
            megabits = float(raw)
        except ValueError:
            log.debug('pan_firewall: interface %s has an unparseable speed %r: it is not sent', name, raw)
            continue
        if megabits != megabits or megabits in (float('inf'), float('-inf')):
            log.debug('pan_firewall: interface %s has an unparseable speed %r: it is not sent', name, raw)
            continue
        samples.append(Sample('interface.speed', megabits * MEGABIT, interface_tags(name, state, serial), 'gauge'))
    return samples


@register('interfaces')
def collect_interfaces(ctx: CollectContext) -> list[Sample]:
    root = ctx.client.op(COUNTER_INTERFACE_CMD)
    serial = ctx.identity.serial
    return [
        *parse_interface_counters(root, ctx.state, serial, ctx.state.tunnel_tags, ctx.log),
        *parse_interface_speeds(ctx.state, serial, ctx.log),
    ]
