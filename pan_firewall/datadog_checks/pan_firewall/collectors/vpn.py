# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""IPSec tunnels (`show vpn flow`) and IKE gateways (`show vpn gateway`).

The tunnel byte and packet counters come from `counter interface all`, owned by the `interfaces` collector: this one
stores the tunnel tags in the state for it, and the tunnel states for the interface metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from . import CollectContext, Sample, once_log, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

VPN_FLOW_CMD = '<show><vpn><flow/></vpn></show>'
VPN_GATEWAY_CMD = '<show><vpn><gateway/></vpn></show>'

# `show vpn flow` state -> `ipsec.tunnel.state` value.
STATE_VALUES = {'inactive': 0, 'active': 1, 'init': 2}


@dataclass
class VpnSnapshot:
    samples: list[Sample] = field(default_factory=list)
    tunnel_tags: dict[str, tuple[str, ...]] = field(default_factory=dict)  # by inner interface
    tunnel_states: dict[str, str] = field(default_factory=dict)  # raw state by inner interface


def parse_vpn(flow: Element, gateway: Element, log: CheckLoggingAdapter) -> VpnSnapshot:
    """Tunnel totals, gateway total and per-tunnel state. A reply without `result` gives no samples and a warning."""
    flow_result, gateway_result = flow.find('result'), gateway.find('result')
    if flow_result is None or gateway_result is None:
        log.warning('`show vpn flow` or `show vpn gateway` has no result: no IPSec metrics are sent')
        return VpnSnapshot()
    gateway_entries = gateway_result.findall('./entries/entry')
    # Only for the tunnels' `gateway` tag: an entry without an id or a name still counts in the total.
    gateways = {
        gwid: name for entry in gateway_entries if (gwid := text(entry, 'id')) and (name := text(entry, 'name'))
    }
    entries = flow_result.findall('./IPSec/entry')
    snapshot = VpnSnapshot()
    counts = dict.fromkeys(STATE_VALUES, 0)
    for entry in entries:
        state = text(entry, 'state') or ''
        interface = text(entry, 'inner-if')
        values = (
            ('tunnel', text(entry, 'name')),
            ('tunnel_interface', interface),
            ('peer_ip', text(entry, 'peerip')),
            ('gateway', gateways.get(text(entry, 'gwid') or '')),
            ('outer_interface', text(entry, 'outer-if')),
        )
        tags = tuple(f'{key}:{value}' for key, value in values if value)
        if interface:
            snapshot.tunnel_tags[interface] = tags
            snapshot.tunnel_states[interface] = state
        if state not in STATE_VALUES:
            log.warning('IPSec tunnel %s has an unknown state %r: its state is not sent', tags, state)
            continue
        counts[state] += 1
        snapshot.samples.append(Sample('ipsec.tunnel.state', STATE_VALUES[state], tags, 'gauge'))
    totals = (
        ('ipsec.tunnels.total', len(entries)),
        ('ipsec.tunnels.active', counts['active']),
        ('ipsec.tunnels.inactive', counts['inactive']),
        ('ipsec.tunnels.init', counts['init']),
        ('ipsec.gateways.total', len(gateway_entries)),
    )
    snapshot.samples[:0] = [Sample(name, value, (), 'gauge') for name, value in totals]
    return snapshot


@register('vpn')
def collect_vpn(ctx: CollectContext) -> list[Sample]:
    flow = ctx.client.op(VPN_FLOW_CMD)
    gateway = ctx.client.op(VPN_GATEWAY_CMD)
    snapshot = parse_vpn(flow, gateway, once_log(ctx))
    if snapshot.samples:
        ctx.state.tunnel_tags = snapshot.tunnel_tags
        ctx.state.tunnel_states = snapshot.tunnel_states
    return snapshot.samples
