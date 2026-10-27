# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""High availability: the local HA state from `show high-availability all`, kept for the other collectors, and the
link counters from one `show high-availability interface <link>` call per configured link."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import num, tag_tuple, text

from .base import CollectContext, Sample

HA_CMD = '<show><high-availability><all/></high-availability></show>'
HA_INTERFACE_CMD = '<show><high-availability><interface>{link}</interface></high-availability></show>'
# A link is queried when `local-info/<link>-port` names a port.
HA_LINKS = ('ha1', 'ha2')

# The management port (typically HA1) answers `result/entry/counters`; a dataplane port (HA2, or HA1 on a dedicated
# port) answers `result/entry/ifnet/counters/hw/entry/port`, whose `ifnet` siblings count what the dataplane forwarded
# and so differ from the port's own counters.
MANAGEMENT_COUNTERS = 'result/entry/counters'
DATAPLANE_COUNTERS = 'result/entry/ifnet/counters/hw/entry/port'

# Metric to the management counter, and to the dataplane counters (summed for the packet counts).
MANAGEMENT_FIELDS = {
    'ha.interface.rx.bytes': ('rx-bytes',),
    'ha.interface.rx.packets': ('rx-packets',),
    'ha.interface.rx.errors': ('rx-errs',),
    'ha.interface.rx.drops': ('rx-drop',),
    'ha.interface.tx.bytes': ('tx-bytes',),
    'ha.interface.tx.packets': ('tx-packets',),
}
DATAPLANE_FIELDS = {
    'ha.interface.rx.bytes': ('rx-bytes',),
    'ha.interface.rx.packets': ('rx-unicast', 'rx-multicast', 'rx-broadcast'),
    'ha.interface.rx.errors': ('rx-error',),
    'ha.interface.rx.drops': ('rx-discards',),
    'ha.interface.tx.bytes': ('tx-bytes',),
    'ha.interface.tx.packets': ('tx-unicast', 'tx-multicast', 'tx-broadcast'),
}


def collect_ha(ctx: CollectContext) -> list[Sample]:
    """Set `ctx.state.ha_state` (None when HA is off) before any link call, so that a failing link call still leaves
    the state for the device metadata, then collect the counters of each configured link."""
    root = ctx.client.op(HA_CMD)
    if (text(root, 'result/enabled') or '').lower() != 'yes':
        ctx.state.ha_state = None
        return []
    ctx.state.ha_state = text(root, 'result/group/local-info/state')
    samples: list[Sample] = []
    for link in HA_LINKS:
        if not text(root, f'result/group/local-info/{link}-port'):
            continue
        link_samples = parse_ha_interface(ctx.client.op(HA_INTERFACE_CMD.format(link=link)), link)
        if link_samples is None:
            ctx.warning(f'unrecognized answer for the high availability link {link}', key=f'ha_interface:{link}')
            continue
        samples.extend(link_samples)
    return samples


def parse_ha_interface(root: Element, link: str) -> list[Sample] | None:
    """The counters of an HA link, by the shape of the answer rather than the link name; None for an unknown shape."""
    for path, fields in ((MANAGEMENT_COUNTERS, MANAGEMENT_FIELDS), (DATAPLANE_COUNTERS, DATAPLANE_FIELDS)):
        counters = root.find(path)
        if counters is not None:
            tags = tag_tuple(('ha_link', link))
            samples = []
            for name, names in fields.items():
                values = [num(counters, field) for field in names]
                if all(value is not None for value in values):
                    samples.append(Sample(name, sum(v for v in values if v is not None), tags, 'monotonic_count'))
            return samples
    return None
