# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Network Device Monitoring metadata payloads.

The device id is ``{namespace}:{managementIpAddress}``, which is the same identity the Agent's
SNMP check computes. That is deliberate and is the whole point of the pairing: Catalyst Center
supplies inventory, health and RF context while SNMP supplies high-resolution counters, and the
two only merge into one device in the NDM view if the ids agree exactly. A namespace mismatch
does not error -- it silently produces two half-populated devices.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

INTEGRATION = 'cisco_catalyst_center'
VENDOR = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100

STATUS_REACHABLE = 1
STATUS_UNREACHABLE = 2

STATUS_UP = 1
STATUS_DOWN = 2
OPER_STATUS_UNKNOWN = 4

KBPS_TO_BPS = 1000

# Values the data API uses for a reachable device. The legacy endpoint answers `Reachable` in
# title case while the data API answers `REACHABLE`, so both are accepted.
REACHABLE_VALUES = frozenset({'REACHABLE', 'Reachable', 'reachable'})
UP_VALUES = frozenset({'UP', 'up', 'Up'})

# The device types NDM understands. Anything unmapped becomes 'other' rather than being invented,
# since an unrecognised value is dropped downstream.
# https://github.com/DataDog/datadog-agent/blob/main/pkg/collector/corechecks/snmp/internal/report/report_device_metadata.go
DEVICE_FAMILY_TO_TYPE = {
    'Switches and Hubs': 'switch',
    'Routers': 'router',
    'Unified AP': 'access_point',
    'Wireless Controller': 'wlc',
    'Security and VPN': 'firewall',
    'Sensors': 'sensor',
}


class DeviceMetadata(BaseModel):
    integration: str = INTEGRATION
    id: str
    id_tags: list[str]
    tags: list[str]
    ip_address: str
    status: int
    name: str
    vendor: str = VENDOR
    serial_number: str = ''
    location: str = ''
    version: str = ''
    product_name: str = ''
    os_name: str = ''
    device_type: str = 'other'
    site_id: str = ''
    site_name: str = ''
    stack_role: str | None = None
    namespace: str


class InterfaceMetadata(BaseModel):
    integration: str = INTEGRATION
    device_id: str
    raw_id: str
    raw_id_type: str = 'interface_uuid'
    id_tags: list[str]
    name: str
    description: str = ''
    mac_address: str = ''
    admin_status: int | None = None
    oper_status: int = OPER_STATUS_UNKNOWN
    speed: int | None = None
    vlan: int | None = None
    port_role: str | None = None


class NetworkDevicesMetadata(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    integration: str = INTEGRATION
    namespace: str
    devices: list[DeviceMetadata] = Field(default_factory=list)
    interfaces: list[InterfaceMetadata] = Field(default_factory=list)
    collect_timestamp: int | None = None
    size: int = Field(default=0, exclude=True)

    def append(self, item: DeviceMetadata | InterfaceMetadata) -> None:
        if isinstance(item, DeviceMetadata):
            self.devices.append(item)
        else:
            self.interfaces.append(item)
        self.size += 1


def _site_name(hierarchy: str | None) -> str:
    """The leaf of the hierarchy path. There is no siteName field on any of these records."""
    parts = [segment for segment in (hierarchy or '').strip().split('/') if segment]
    return parts[-1] if parts else ''


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def create_device_metadata(record: dict[str, Any], namespace: str, stack_role: str | None = None) -> DeviceMetadata:
    """Build the NDM device payload from one ``data/networkDevices`` record.

    Field names differ from those the product brief lists, because the brief maps against the
    legacy inventory endpoint: the data API has ``name`` rather than ``hostname``, ``osType``
    rather than ``softwareType``, and ``reachabilityHealthStatus`` rather than
    ``reachabilityStatus``.
    """
    management_ip = record.get('managementIpAddress') or ''
    hierarchy = record.get('siteHierarchy')

    # The record identity is Catalyst Center's own instanceUuid, per the product brief. It is
    # present on every record, whereas managementIpAddress is not -- an access point reporting
    # through a controller may have none, and an IP-derived id would collapse every such device
    # onto a single record.
    device_uuid = record.get('id') or ''

    # The SNMP check identifies the same hardware as {namespace}:{ip}, so that form is carried as
    # a tag. This is what lines the two sources up; the namespace must match the SNMP check's.
    snmp_device_id = f'{namespace}:{management_ip}'

    id_tags = [
        f'device_namespace:{namespace}',
        f'device_ip:{management_ip}',
        f'device_id:{snmp_device_id}',
    ]
    tags = [
        *id_tags,
        f'device_uuid:{device_uuid}',
        f'device_hostname:{record.get("name") or ""}',
        f'device_family:{record.get("deviceFamily") or ""}',
        f'device_role:{record.get("deviceRole") or ""}',
        f'device_series:{record.get("deviceSeries") or ""}',
        f'device_vendor:{VENDOR}',
    ]

    return DeviceMetadata(
        id=device_uuid,
        id_tags=id_tags,
        tags=tags,
        ip_address=management_ip,
        status=STATUS_REACHABLE if record.get('reachabilityHealthStatus') in REACHABLE_VALUES else STATUS_UNREACHABLE,
        name=record.get('name') or '',
        serial_number=record.get('serialNumber') or '',
        location=hierarchy or '',
        version=record.get('softwareVersion') or '',
        product_name=record.get('platformId') or '',
        os_name=record.get('osType') or '',
        device_type=DEVICE_FAMILY_TO_TYPE.get(record.get('deviceFamily') or '', 'other'),
        site_id=record.get('siteId') or '',
        site_name=_site_name(hierarchy),
        # Cisco reports ACTIVE / STANDBY / MEMBER here, not the master/member the brief names.
        # Only known for stackable families, and only once the stack collector has run.
        stack_role=stack_role,
        namespace=namespace,
    )


def _port_role(record: dict[str, Any]) -> str | None:
    """Classify a port as uplink, access or trunk.

    The brief derives this from ``interfaceType``, ``portMode`` and the description. ``isWan``
    takes precedence when the appliance sets it, because that is the appliance's own judgement
    about which link leaves the site rather than an inference from port mode.
    """
    if record.get('isWan'):
        return 'uplink'
    port_mode = record.get('portMode')
    return str(port_mode) if port_mode else None


def create_interface_metadata(record: dict[str, Any], namespace: str) -> InterfaceMetadata:
    """Build the NDM interface payload from one merged ``data/interfaces`` record.

    ``device_id`` is the parent device's instanceUuid, matching the id assigned in
    :func:`create_device_metadata`. The interface record already carries it as
    ``networkDeviceId``, so the parent is resolved directly rather than joined through an IP.

    ``speed`` is documented in Kbps and returned as a string, while NDM expects bits per second.
    """
    name = record.get('name') or ''
    speed_kbps = _int_or_none(record.get('speed'))

    return InterfaceMetadata(
        device_id=record.get('networkDeviceId') or '',
        raw_id=record.get('id') or '',
        id_tags=[f'interface:{name}'],
        name=name,
        description=record.get('description') or '',
        mac_address=record.get('macAddress') or '',
        admin_status=STATUS_UP if record.get('adminStatus') in UP_VALUES else STATUS_DOWN,
        oper_status=STATUS_UP if record.get('operStatus') in UP_VALUES else STATUS_DOWN,
        speed=speed_kbps * KBPS_TO_BPS if speed_kbps is not None else None,
        vlan=_int_or_none(record.get('vlanId')),
        port_role=_port_role(record),
    )


def batch_payloads(
    namespace: str,
    items: list[DeviceMetadata] | list[InterfaceMetadata],
    collect_timestamp: int | None = None,
) -> Iterator[NetworkDevicesMetadata]:
    """Split metadata into payloads of at most 100 items."""
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
