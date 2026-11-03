# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from collections.abc import Iterable, Iterator

from pydantic import BaseModel, ConfigDict, Field

from .constants import DEVICE_VENDOR_TAG

INTEGRATION = 'pan_firewall'
PAYLOAD_METADATA_BATCH_SIZE = 100

STATUS_REACHABLE = 1
STATUS_UNREACHABLE = 2
OPER_UP = 1
OPER_DOWN = 2
OPER_UNKNOWN = 4
ADMIN_UP = 1
ADMIN_DOWN = 2


class DeviceMetadata(BaseModel):
    integration: str = INTEGRATION
    id: str
    id_tags: list[str]
    tags: list[str]
    ip_address: str
    status: int
    name: str | None = None
    model: str | None = None
    serial_number: str
    version: str | None = None
    # Same value as the `device_vendor` tag and the SNMP profile, so that NDM derives no second vendor tag.
    vendor: str = DEVICE_VENDOR_TAG
    os_name: str = 'PAN-OS'
    device_type: str = 'firewall'
    namespace: str


class InterfaceMetadata(BaseModel):
    integration: str = INTEGRATION
    device_id: str
    raw_id: str
    raw_id_type: str = 'name'
    id_tags: list[str]
    name: str
    index: int | None = None
    mac_address: str | None = None
    description: str | None = None
    admin_status: int | None = None
    oper_status: int


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


def batch_payloads(
    namespace: str, items: Iterable[DeviceMetadata | InterfaceMetadata], collect_timestamp: int | None = None
) -> Iterator[NetworkDevicesMetadata]:
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
