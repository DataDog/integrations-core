# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Routing protocol sessions: BGP peers and OSPF neighbors.

The legacy routing engine answers `show routing protocol bgp peer` and `... ospf neighbor`. The Advanced Routing Engine
(ARE) answers `show advanced-routing ...` with JSON inside `result/json`, one call per logical router, and the logical
router name fills the `vr` tag. OSPF neighbors on the ARE are not collected yet.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal
from xml.etree.ElementTree import Element
from xml.sax.saxutils import escape

from datadog_checks.pan_firewall.errors import PanosError
from datadog_checks.pan_firewall.xml_utils import num, tag_tuple, text

from .base import CollectContext, Sample

BGP_PEER_CMD = '<show><routing><protocol><bgp><peer/></bgp></protocol></routing></show>'
OSPF_NEIGHBOR_CMD = '<show><routing><protocol><ospf><neighbor/></ospf></protocol></routing></show>'

ARE_LOGICAL_ROUTER_CMD = '<show><advanced-routing><logical-router/></advanced-routing></show>'
ARE_BGP_PEER_CMD = (
    '<show><advanced-routing><bgp><peer><detail><logical-router>{router}</logical-router></detail></peer></bgp>'
    '</advanced-routing></show>'
)

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
    """`169.254.10.2:179` -> `169.254.10.2`. IPv6 is expected as `[2001:db8::1]:179` or bare; a bare one is kept as
    is, since its port cannot be told from an address group."""
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


def camel_afi_safi_tag(name: str) -> str:
    """`ipv4Unicast` -> `ipv4_unicast`."""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name).lower()


def bgp_restart(established: bool, duration: float) -> int:
    return 1 if established and duration < RESTART_WINDOW_SECONDS else 0


def parse_bgp_peers(root: Element) -> list[Sample]:
    samples: list[Sample] = []
    for entry in root.iterfind('result/entry'):
        tags = tag_tuple(
            ('peer', entry.get('peer')),
            ('vr', entry.get('vr')),
            ('peer_ip', peer_ip(text(entry, 'peer-address'))),
            ('remote_as', text(entry, 'remote-as')),
            ('peer_group', text(entry, 'peer-group')),
        )
        established = text(entry, 'status') == 'Established'
        duration = num(entry, 'status-duration')
        samples.append(Sample('bgp.peer.status', 1 if established else 0, tags, 'gauge'))
        if duration is not None:
            samples.append(Sample('bgp.peer.restart', bgp_restart(established, duration), tags, 'gauge'))
        for name, path, kind in BGP_NUMBERS:
            value = num(entry, path)
            if value is not None:
                samples.append(Sample(f'bgp.peer.{name}', value, tags, kind))

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


def are_json(root: Element) -> dict:
    """The JSON object in `result/json` of an ARE answer; `{}` when missing or empty.

    Raises PanosError when the text is not a JSON object, so that a broken answer is reported as a failed call.
    """
    body = text(root, 'result/json')
    if body is None:
        return {}
    try:
        data = json.loads(body)
    except ValueError as e:
        raise PanosError(f'the Advanced Routing Engine answer is not valid JSON: {e}') from e
    if not isinstance(data, dict):
        raise PanosError(f'the Advanced Routing Engine answer is a JSON {type(data).__name__}, expected an object')
    return data


def json_num(data: Any, key: str) -> float | None:
    """The number at `key` of a JSON object; None when missing, not a number or not finite."""
    value = data.get(key) if isinstance(data, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def json_str(data: dict, key: str) -> str | None:
    value = data.get(key)
    return None if value is None else str(value)


def logical_routers(ctx: CollectContext) -> list[str]:
    """The names of the logical routers; warns once per firewall when the answer lists none."""
    routers = list(are_json(ctx.client.op(ARE_LOGICAL_ROUTER_CMD)))
    if not routers:
        ctx.warning('the Advanced Routing Engine lists no logical router', key='are_logical_router')
    return routers


def parse_are_bgp_peers(data: dict, router: str) -> list[Sample]:
    samples: list[Sample] = []
    for name, peer in data.items():
        if not isinstance(peer, dict):
            continue
        tags = tag_tuple(
            ('peer', name),
            ('vr', router),
            ('peer_ip', json_str(peer, 'peer-ip')),
            ('remote_as', json_str(peer, 'remote-as')),
            ('peer_group', json_str(peer, 'peer-group-name')),
        )
        established = peer.get('state') == 'Established'
        samples.append(Sample('bgp.peer.status', 1 if established else 0, tags, 'gauge'))
        duration = json_num(peer, 'status-time')
        if duration is not None:
            samples.append(Sample('bgp.peer.status_duration', duration, tags, 'gauge'))
            samples.append(Sample('bgp.peer.restart', bgp_restart(established, duration), tags, 'gauge'))

        detail = peer.get('detail')
        if not isinstance(detail, dict):
            continue
        counters = detail.get('messageStats')
        for metric, source, key in (
            ('updates.in', counters, 'updatesRecv'),
            ('updates.out', counters, 'updatesSent'),
            ('connections.established', detail, 'connectionsEstablished'),
            ('connections.dropped', detail, 'connectionsDropped'),
        ):
            value = json_num(source, key)
            if value is not None:
                samples.append(Sample(f'bgp.peer.{metric}', value, tags, 'monotonic_count'))

        families = detail.get('addressFamilyInfo')
        for family_name, family in families.items() if isinstance(families, dict) else ():
            family_tags = (*tags, f'afi_safi:{camel_afi_safi_tag(family_name)}')
            limit = json_num(family, 'prefixAllowedMax')
            accepted = json_num(family, 'acceptedPrefixCounter')
            for metric, value in (
                ('prefix_limit', limit),
                ('prefixes.incoming.total', accepted),
                ('prefixes.outgoing.advertised', json_num(family, 'sentPrefixCounter')),
            ):
                if value is not None:
                    samples.append(Sample(f'bgp.peer.{metric}', value, family_tags, 'gauge'))
            if accepted is not None and limit:
                samples.append(
                    Sample('bgp.peer.prefix_limit.utilization', accepted / limit * 100, family_tags, 'gauge')
                )
    return samples


def parse_ospf_neighbors(root: Element) -> list[Sample]:
    samples: list[Sample] = []
    for entry in root.iterfind('result/entry'):
        state = text(entry, 'status')
        if state is None:
            continue
        tags = tag_tuple(
            ('neighbor', text(entry, 'neighbor-address')),
            ('router_id', text(entry, 'neighbor-router-id')),
            ('area', text(entry, 'area-id')),
            ('vr', text(entry, 'virtual-router')),
        )
        samples.append(Sample('ospf.neighbor.status', 1 if state.lower() == 'full' else 0, tags, 'gauge'))
    return samples


def legacy_routing_engine(ctx: CollectContext) -> bool:
    """False, with one warning per firewall, when the firewall runs the Advanced Routing Engine."""
    if not ctx.identity.advanced_routing:
        return True
    ctx.warning(
        'the firewall runs the Advanced Routing Engine: OSPF metrics need the legacy '
        'routing engine and are not reported',
        key='advanced_routing',
    )
    return False


def collect_bgp(ctx: CollectContext) -> list[Sample]:
    if ctx.identity.advanced_routing is not True:
        return parse_bgp_peers(ctx.client.op(BGP_PEER_CMD))
    samples: list[Sample] = []
    for router in logical_routers(ctx):
        data = are_json(ctx.client.op(ARE_BGP_PEER_CMD.format(router=escape(router))))
        samples.extend(parse_are_bgp_peers(data, router))
    return samples


def collect_ospf(ctx: CollectContext) -> list[Sample]:
    if not legacy_routing_engine(ctx):
        return []
    return parse_ospf_neighbors(ctx.client.op(OSPF_NEIGHBOR_CMD))
