# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Routing protocol sessions: BGP peers of the legacy routing engine.

The Advanced Routing Engine (ARE) answers `show routing protocol bgp peer` differently, and has no parser yet.
"""

from __future__ import annotations

import re
from typing import Literal
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import num, text

from . import CollectContext, Sample, register

BGP_PEER_CMD = '<show><routing><protocol><bgp><peer/></bgp></protocol></routing></show>'

# A peer that came up less than this long ago has restarted.
RESTART_WINDOW_SECONDS = 1800

BGP_NUMBERS: tuple[tuple[str, str, Literal['gauge', 'monotonic_count']], ...] = (
    ('status_duration', 'status-duration', 'gauge'),
    ('updates.in', 'msg-update-in', 'monotonic_count'),
    ('updates.out', 'msg-update-out', 'monotonic_count'),
    ('prefix_limit', 'prefix-limit', 'gauge'),
)
BGP_PREFIXES = (
    ('incoming.total', 'incoming-total'),
    ('incoming.rejected', 'incoming-rejected'),
    ('outgoing.total', 'outgoing-total'),
    ('outgoing.advertised', 'outgoing-advertised'),
)


def peer_ip(address: str | None) -> str | None:
    """Return the address of a PAN-OS `peer-address`, without its port.

    Seen as `169.254.10.2:179`; IPv6 is expected as `[2001:db8::1]:179` or bare. A bare IPv6 has several colons and
    is returned as is, since the port cannot be told from an address group.
    """
    if not address:
        return None
    if address.startswith('['):
        return address[1:].partition(']')[0] or None
    if address.count(':') == 1:
        return address.partition(':')[0]
    return address


def afi_safi_tag(name: str) -> str:
    """`bgpAfiIpv4-unicast` -> `ipv4_unicast`."""
    return re.sub(r'(?i)^bgpafi', '', name).replace('-', '_').lower()


def parse_bgp_peers(root: Element) -> list[Sample]:
    samples: list[Sample] = []
    for entry in root.iterfind('result/entry'):
        tags = [
            f'{tag}:{value}'
            for tag, value in (
                ('peer', entry.get('peer')),
                ('vr', entry.get('vr')),
                ('peer_ip', peer_ip(text(entry, 'peer-address'))),
                ('remote_as', text(entry, 'remote-as')),
                ('peer_group', text(entry, 'peer-group')),
            )
            if value
        ]
        established = text(entry, 'status') == 'Established'
        duration = num(entry, 'status-duration')
        samples.append(Sample('bgp.peer.status', 1 if established else 0, tuple(tags), 'gauge'))
        if duration is not None:
            restart = established and duration < RESTART_WINDOW_SECONDS
            samples.append(Sample('bgp.peer.restart', 1 if restart else 0, tuple(tags), 'gauge'))
        for name, path, kind in BGP_NUMBERS:
            value = num(entry, path)
            if value is not None:
                samples.append(Sample(f'bgp.peer.{name}', value, tuple(tags), kind))

        limit = num(entry, 'prefix-limit')
        for family in entry.iterfind('prefix-counter/entry'):
            family_tags = (*tags, f'afi_safi:{afi_safi_tag(family.get("afi-safi", ""))}')
            for name, path in BGP_PREFIXES:
                value = num(family, path)
                if value is not None:
                    samples.append(Sample(f'bgp.peer.prefixes.{name}', value, family_tags, 'gauge'))
            received = num(family, 'incoming-total')
            if received is not None and limit:
                samples.append(
                    Sample('bgp.peer.prefix_limit.utilization', received / limit * 100, family_tags, 'gauge')
                )
    return samples


@register('bgp')
def collect_bgp(ctx: CollectContext) -> list[Sample]:
    if ctx.identity.advanced_routing:
        if not ctx.state.are_warned:
            ctx.state.are_warned = True
            ctx.log.warning(
                'pan_firewall: the firewall runs the Advanced Routing Engine: BGP and OSPF metrics need the legacy '
                'routing engine and are not reported'
            )
        return []
    return parse_bgp_peers(ctx.client.op(BGP_PEER_CMD))
