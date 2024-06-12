# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import six

if six.PY3:
    from typing import Optional

    from pydantic import BaseModel, Field, computed_field

    class NodeAttributes(BaseModel):
        address: Optional[str] = None
        ad_st: Optional[str] = Field(default=None, alias="adSt")
        role: Optional[str] = None
        dn: Optional[str] = None
        model: Optional[str] = None
        version: Optional[str] = None
        serial: Optional[str] = None
        vendor: Optional[str] = Field(default='cisco-aci')
        namespace: Optional[str] = Field(default='default')

        @computed_field
        @property
        def device_type(self) -> str:
            if self.role in ['leaf', 'spine']:
                return 'switch'
            if self.role in ['controller', 'vleaf', 'vip', 'protection-chain']:
                return 'cisco_aci'
            return 'other'

    class Node(BaseModel):
        attributes: NodeAttributes

    class EthAttributes(BaseModel):
        admin_st: Optional[str] = Field(default=None, alias="adminSt")
        id: Optional[str] = None
        name: Optional[str] = None
        desc: Optional[str] = None
        router_mac: Optional[str] = Field(default=None, alias="routerMac")

    class Eth(BaseModel):
        attributes: EthAttributes

    class DeviceMetadata(BaseModel):
        id: Optional[str] = Field(default=None)
        id_tags: list = Field(default_factory=list)
        tags: list = Field(default_factory=list)
        name: Optional[str] = Field(default=None)
        ip_address: Optional[str] = Field(default=None)
        model: Optional[str] = Field(default=None)
        ad_st: Optional[str] = Field(default=None, exclude=True)
        vendor: Optional[str] = Field(default=None)
        version: Optional[str] = Field(default=None)
        serial_number: Optional[str] = Field(default=None)
        device_type: Optional[str] = Field(default=None)
        integration: Optional[str] = Field(default='cisco-aci')

        @computed_field
        @property
        def status(self) -> int:
            return 1 if self.ad_st == 'on' else 2

    class DeviceMetadataList(BaseModel):
        device_metadata: list = Field(default_factory=list)

    class InterfaceMetadata(BaseModel):
        device_id: Optional[str] = Field(default=None)
        id_tags: list = Field(default_factory=list)
        index: Optional[str] = Field(default=None)
        name: Optional[str] = Field(default=None)
        description: Optional[str] = Field(default=None)
        mac_address: Optional[str] = Field(default=None)
        admin_status: Optional[str] = Field(default=None, exclude=True)

        @computed_field
        @property
        def status(self) -> int:
            return 1 if self.admin_status == 'up' else 2

    class InterfaceMetadataList(BaseModel):
        interface_metadata: list = Field(default_factory=list)

    class NetworkDevicesMetadata(BaseModel):
        subnet: Optional[str] = None
        namespace: str = None
        devices: Optional[list[DeviceMetadata]] = Field(default_factory=list)
        interfaces: Optional[list[InterfaceMetadata]] = Field(default_factory=list)
        collect_timestamp: Optional[float] = None
