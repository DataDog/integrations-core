# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from .parsers.tunnel import parse_tunnel_alias

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

    from .models import Appliance
    from .parsers.tunnel import TunnelV2Stats

INTEGRATION = 'hpe_aruba_edgeconnect'
VENDOR = 'aruba'
OS_NAME = 'ECOS'
PAYLOAD_METADATA_BATCH_SIZE = 100

STATUS_REACHABLE = 1
STATUS_UNREACHABLE = 2

ADMIN_STATUS_UP = 1
ADMIN_STATUS_DOWN = 2
OPER_STATUS_UP = 1
OPER_STATUS_DOWN = 2

_VLAN_RE = re.compile(r':v(\d+)$')

# https://github.com/DataDog/datadog-agent/blob/main/pkg/collector/corechecks/snmp/internal/report/report_device_metadata.go#L46C1-L61C2
SUPPORTED_DEVICE_TYPES = frozenset(
    {
        'access_point',
        'firewall',
        'load_balancer',
        'pdu',
        'printer',
        'router',
        'sd-wan',
        'sensor',
        'server',
        'storage',
        'switch',
        'ups',
        'wlc',
    }
)


class DeviceMetadata(BaseModel):
    integration: str = INTEGRATION
    id: str
    id_tags: list[str]
    tags: list[str]
    ip_address: str
    status: int
    name: str
    vendor: str
    serial_number: str
    location: str
    version: str
    product_name: str
    os_name: str
    device_type: str
    site_id: str
    site_name: str
    namespace: str


class InterfaceMetadata(BaseModel):
    integration: str = INTEGRATION
    device_id: str
    raw_id: str
    raw_id_type: str = 'name'
    id_tags: list[str]
    name: str
    mac_address: str
    admin_status: int
    oper_status: int
    vlan: int | None = None


class TunnelMetadata(BaseModel):
    integration: str = INTEGRATION
    tunnel_id: str
    src_device_id: str
    dst_device_id: str
    src_site_id: str | None = None
    dst_site_id: str
    overlay_name: str
    path_name: str
    tunnel_color: str


class NetworkDevicesMetadata(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    integration: str = INTEGRATION
    namespace: str | None = None
    devices: list[DeviceMetadata] = Field(default_factory=list)
    interfaces: list[InterfaceMetadata] = Field(default_factory=list)
    tunnels: list[TunnelMetadata] = Field(default_factory=list)
    collect_timestamp: int | None = None
    size: int = Field(default=0, exclude=True)

    def append(self, item: DeviceMetadata | InterfaceMetadata | TunnelMetadata) -> None:
        if isinstance(item, DeviceMetadata):
            self.devices.append(item)
        elif isinstance(item, InterfaceMetadata):
            self.interfaces.append(item)
        elif isinstance(item, TunnelMetadata):
            self.tunnels.append(item)
        self.size += 1


def create_device_metadata(appliance: Appliance, namespace: str) -> DeviceMetadata:
    device_id = f'{namespace}:{appliance.ip}'
    site = appliance.site or 'unknown'
    return DeviceMetadata(
        id=device_id,
        id_tags=[
            f'device_namespace:{namespace}',
            f'device_ip:{appliance.ip}',
        ],
        tags=[
            f'device_namespace:{namespace}',
            f'device_ip:{appliance.ip}',
            f'device_hostname:{appliance.host_name}',
            f'device_id:{device_id}',
        ],
        ip_address=appliance.ip,
        status=STATUS_REACHABLE if appliance.state == 1 else STATUS_UNREACHABLE,
        name=appliance.host_name,
        vendor=VENDOR,
        serial_number=appliance.serial,
        location=site,
        version=appliance.software_version,
        product_name=appliance.model,
        os_name=OS_NAME,
        device_type=appliance.mode if appliance.mode in SUPPORTED_DEVICE_TYPES else 'other',
        site_id=site,
        site_name=site,
        namespace=namespace,
    )


def create_interface_metadata(appliance_ip: str, iface: dict[str, Any], namespace: str) -> InterfaceMetadata:
    ifname = iface.get('ifname', '')
    return InterfaceMetadata(
        device_id=f'{namespace}:{appliance_ip}',
        raw_id=ifname,
        id_tags=[f'interface:{ifname}'],
        name=ifname,
        mac_address=iface.get('mac', ''),
        admin_status=_bool_to_status(iface.get('admin'), ADMIN_STATUS_UP, ADMIN_STATUS_DOWN),
        oper_status=_bool_to_status(iface.get('oper'), OPER_STATUS_UP, OPER_STATUS_DOWN),
        vlan=_parse_vlan(ifname),
    )


def create_tunnel_metadata(
    tunnel: TunnelV2Stats,
    appliance_ip: str,
    src_site: str,
    namespace: str,
    peer_lookup: dict[str, tuple[str, str]],
    overlay_map: dict[str, str],
    log: CheckLoggingAdapter,
) -> TunnelMetadata:
    peer_hostname, wan_labels = parse_tunnel_alias(tunnel.tunnel_alias)
    if not peer_hostname:
        log.debug("Peer hostname is not present on the tunnel alias %r", peer_hostname, tunnel.tunnel_alias)
    peer_ip, peer_site = peer_lookup.get(peer_hostname, ('', ''))
    if peer_hostname and not peer_ip:
        log.warning(
            "Could not find peer %r for tunnel %r in peer lookup, dst_device_id will be empty",
            peer_hostname,
            tunnel.tunnel_alias,
        )
    return TunnelMetadata(
        tunnel_id=tunnel.tunnel_id,
        src_device_id=f'{namespace}:{appliance_ip}',
        dst_device_id=f'{namespace}:{peer_ip}' if peer_ip else '',
        src_site_id=src_site or 'unknown',
        dst_site_id=peer_site or 'unknown',
        overlay_name=overlay_map.get(tunnel.overlay_id, tunnel.overlay_id),
        path_name=tunnel.tunnel_alias,
        tunnel_color=wan_labels,
    )


def batch_payloads(
    namespace: str,
    items: list[DeviceMetadata | InterfaceMetadata | TunnelMetadata],
    collect_timestamp: int | None = None,
) -> Iterator[NetworkDevicesMetadata]:
    if not items:
        return
    if collect_timestamp is None:
        collect_timestamp = int(time.time())

    payload = NetworkDevicesMetadata(namespace=namespace, collect_timestamp=collect_timestamp)
    for item in items:
        if payload.size >= PAYLOAD_METADATA_BATCH_SIZE:
            yield payload
            payload = NetworkDevicesMetadata(namespace=namespace, collect_timestamp=collect_timestamp)
        payload.append(item)

    if payload.size > 0:
        yield payload


def _bool_to_status(value: bool | None, up: int, down: int) -> int:
    if value is None:
        return down
    return up if value else down


def _parse_vlan(ifname: str) -> int | None:
    m = _VLAN_RE.search(ifname)
    return int(m.group(1)) if m else None
