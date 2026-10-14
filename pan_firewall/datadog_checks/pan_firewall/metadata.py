# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Builds the NDM device and interface records from what the poller keeps about a firewall."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ndm_models import DeviceMetadata, InterfaceMetadata
from .xml_utils import num, text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from xml.etree.ElementTree import Element

    from .collectors import FirewallState
    from .identity import DeviceIdentity

STATUS_REACHABLE = 1
STATUS_UNREACHABLE = 2
OPER_UP = 1
OPER_DOWN = 2
OPER_UNKNOWN = 4

HW_STATES = {'up': OPER_UP, 'down': OPER_DOWN}
# `show vpn flow` state of a tunnel interface to the NDM operational status: only `active` is up.
VPN_ACTIVE = 'active'
HW_TYPE_PHYSICAL = '0'


def build_device(
    identity: DeviceIdentity,
    ip: str,
    namespace: str,
    tags: list[str],
    can_connect: int,
    ha_state: str | None,
) -> DeviceMetadata:
    """The device record; `identity.serial` must be known. `ha_state` has no NDM field, so it rides in the tags."""
    if identity.serial is None:
        raise ValueError('a device record needs the serial')
    return DeviceMetadata(
        id=identity.serial,
        id_tags=[f'device_namespace:{namespace}', f'device_id:{identity.serial}'],
        tags=[*tags, f'ha_state:{ha_state}'] if ha_state else list(tags),
        ip_address=ip,
        status=STATUS_REACHABLE if can_connect else STATUS_UNREACHABLE,
        name=identity.hostname,
        model=identity.model,
        serial_number=identity.serial,
        version=identity.sw_version,
        namespace=namespace,
    )


def build_interfaces(serial: str, state: FirewallState) -> Iterator[InterfaceMetadata]:
    hw_rows = state.interface_map or {}
    for row in state.interface_rows:
        name = text(row, 'name')
        if not name:
            continue
        hw = hw_rows.get(name)
        index = num(row, 'id')
        physical = hw is not None and text(hw, 'type') == HW_TYPE_PHYSICAL
        yield InterfaceMetadata(
            device_id=serial,
            raw_id=name,
            id_tags=[f'interface:{name}'],
            name=name,
            index=int(index) if index is not None else None,
            mac_address=text(hw, 'mac') if physical else None,
            oper_status=_oper_status(name, hw_rows, state.tunnel_states),
        )


def _oper_status(name: str, hw_rows: dict[str, Element], tunnel_states: dict[str, str]) -> int:
    if name.startswith('loopback'):
        return OPER_UNKNOWN
    if name.startswith('tunnel.'):
        vpn_state = tunnel_states.get(name)
        if vpn_state is None:
            return OPER_UNKNOWN
        return OPER_UP if vpn_state == VPN_ACTIVE else OPER_DOWN
    # A subinterface (`ethernet1/1.10`) has no hw row: it takes its parent's state.
    hw = hw_rows.get(name)
    if hw is None:
        hw = hw_rows.get(name.split('.', 1)[0])
    return HW_STATES.get(text(hw, 'state') or '', OPER_UNKNOWN) if hw is not None else OPER_UNKNOWN
