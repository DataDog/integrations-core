# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""IPSec tunnels (`show vpn flow`) and IKE gateways (`show vpn gateway`).

The tunnel byte and packet counters come from `counter interface all`, owned by the `interfaces` collector: this one
stores the tunnel tags in the state for it, and the tunnel states for the interface metadata.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from .base import CollectContext, Sample, tag_tuple

VPN_FLOW_CMD = '<show><vpn><flow/></vpn></show>'
VPN_GATEWAY_CMD = '<show><vpn><gateway/></vpn></show>'

# `show vpn flow` state -> `ipsec.tunnel.state` value.
STATE_VALUES = {'inactive': 0, 'active': 1, 'init': 2}

# Most-up first: an interface shared by several tunnels takes the best state among them. An unknown state ranks last.
STATE_RANK = ('active', 'init', 'inactive')


@dataclass
class VpnSnapshot:
    samples: list[Sample] = field(default_factory=list)
    tunnel_tags: dict[str, tuple[str, ...]] = field(default_factory=dict)  # by inner interface
    tunnel_states: dict[str, str] = field(default_factory=dict)  # raw state by inner interface


def _state_rank(state: str) -> int:
    return STATE_RANK.index(state) if state in STATE_RANK else len(STATE_RANK)


def parse_vpn(flow: Element, gateway: Element, warn: Callable[..., None]) -> VpnSnapshot:
    """A reply without `result` gives no samples and a warning."""
    flow_result, gateway_result = flow.find('result'), gateway.find('result')
    if flow_result is None or gateway_result is None:
        warn('`show vpn flow` or `show vpn gateway` has no result: no IPSec metrics are sent')
        return VpnSnapshot()
    gateway_entries = gateway_result.findall('./entries/entry')
    # Only for the tunnels' `gateway` tag: an entry without an id or a name still counts in the total.
    gateways = {
        gwid: name for entry in gateway_entries if (gwid := text(entry, 'id')) and (name := text(entry, 'name'))
    }
    entries = flow_result.findall('./IPSec/entry')
    snapshot = VpnSnapshot()
    by_interface: dict[str, list[tuple[str, tuple[str, ...], str | None]]] = {}
    counts = dict.fromkeys(STATE_VALUES, 0)
    for entry in entries:
        state = text(entry, 'state') or ''
        interface = text(entry, 'inner-if')
        tags = tag_tuple(
            ('tunnel', text(entry, 'name')),
            ('tunnel_interface', interface),
            ('peer_ip', text(entry, 'peerip')),
            ('gateway', gateways.get(text(entry, 'gwid') or '')),
            ('outer_interface', text(entry, 'outer-if')),
        )
        if interface:
            by_interface.setdefault(interface, []).append((state, tags, text(entry, 'outer-if')))
        if state not in STATE_VALUES:
            warn('IPSec tunnel %s has an unknown state %r: its state is not sent', tags, state)
            continue
        counts[state] += 1
        snapshot.samples.append(Sample('ipsec.tunnel.state', STATE_VALUES[state], tags, 'gauge'))
    # PAN-OS counts per tunnel interface, and several tunnels can share one (next-hop tunnel binding, or one tunnel
    # with several proxy IDs). The interface-wide counters then can't be attributed to one tunnel: an interface
    # shared by several entries is tagged with the interface only, and is up if any of its tunnels is.
    for interface, tunnels in by_interface.items():
        snapshot.tunnel_states[interface] = min((state for state, _, _ in tunnels), key=_state_rank)
        if len(tunnels) == 1:
            snapshot.tunnel_tags[interface] = tunnels[0][1]
        else:
            outer_interfaces = {outer for _, _, outer in tunnels}
            snapshot.tunnel_tags[interface] = tag_tuple(
                ('tunnel_interface', interface),
                ('outer_interface', outer_interfaces.pop() if len(outer_interfaces) == 1 else None),
            )
    totals = (
        ('ipsec.tunnels.total', len(entries)),
        ('ipsec.tunnels.active', counts['active']),
        ('ipsec.tunnels.inactive', counts['inactive']),
        ('ipsec.tunnels.init', counts['init']),
        ('ipsec.gateways.total', len(gateway_entries)),
    )
    snapshot.samples[:0] = [Sample(name, value, (), 'gauge') for name, value in totals]
    return snapshot


def collect_vpn(ctx: CollectContext) -> list[Sample]:
    flow = ctx.client.op(VPN_FLOW_CMD)
    gateway = ctx.client.op(VPN_GATEWAY_CMD)
    snapshot = parse_vpn(flow, gateway, ctx.warning)
    if snapshot.samples:
        ctx.state.tunnel_tags = snapshot.tunnel_tags
        ctx.state.tunnel_states = snapshot.tunnel_states
    return snapshot.samples
