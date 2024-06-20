# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import six

if six.PY3:
    from typing import Optional

    from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

    class NodeAttributes(BaseModel):
        address: Optional[str] = None
        fabric_st: Optional[str] = Field(default=None, alias="fabricSt")
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

    class EthpmPhysIfAttributes(BaseModel):
        oper_st: Optional[str] = Field(default=None, alias="operSt")
        oper_router_mac: Optional[str] = Field(default=None, alias="operRouterMac")

    class EthpmPhysIf(BaseModel):
        attributes: EthpmPhysIfAttributes

    class L1PhysIfAttributes(BaseModel):
        admin_st: Optional[str] = Field(default=None, alias="adminSt")
        id: Optional[str] = None
        name: Optional[str] = None
        desc: Optional[str] = None
        router_mac: Optional[str] = Field(default=None, alias="routerMac")

    class PhysIf(BaseModel):
        attributes: L1PhysIfAttributes
        children: Optional[list] = Field(default_factory=list)

        @computed_field
        @property
        def ethpm_phys_if(self) -> Optional[EthpmPhysIf]:
            for child in self.children:
                if 'ethpmPhysIf' in child:
                    return EthpmPhysIf(**child['ethpmPhysIf'])
            return None

    class DeviceMetadata(BaseModel):
        id: Optional[str] = Field(default=None)
        id_tags: list = Field(default_factory=list)
        tags: list = Field(default_factory=list)
        name: Optional[str] = Field(default=None)
        ip_address: Optional[str] = Field(default=None)
        model: Optional[str] = Field(default=None)
        fabric_st: Optional[str] = Field(default=None, exclude=True)
        vendor: Optional[str] = Field(default=None)
        version: Optional[str] = Field(default=None)
        serial_number: Optional[str] = Field(default=None)
        device_type: Optional[str] = Field(default=None)
        integration: Optional[str] = Field(default='cisco-aci')

        @computed_field
        @property
        def status(self) -> int:
            mapping = {
                'active': 1,
                'inactive': 2,
                'disabled': 5,
                'discovering': 2,
                'undiscovered': 2,
                'unsupported': 2,
                'unknown': 4,
            }
            return mapping.get(self.fabric_st, 7)

    class DeviceMetadataList(BaseModel):
        device_metadata: list = Field(default_factory=list)

    class InterfaceMetadata(BaseModel):
        device_id: Optional[str] = Field(default=None)
        id_tags: list = Field(default_factory=list)
        index: Optional[str] = Field(default=None)
        name: Optional[str] = Field(default=None)
        description: Optional[str] = Field(default=None)
        mac_address: Optional[str] = Field(default=None)
        admin_status: Optional[int] = Field(default=None)
        oper_status: Optional[int] = Field(default=None)

        model_config = ConfigDict(validate_assignment=True)

        @field_validator("admin_status", mode="before")
        @classmethod
        def parse_admin_status(cls, admin_status: int | None) -> int | None:
            if not admin_status:
                return None

            if admin_status == "up":
                return 1
            return 2

        @field_validator("oper_status", mode="before")
        @classmethod
        def parse_oper_status(cls, oper_status: int | None) -> int | None:
            if not oper_status:
                return None

            if oper_status == "up":
                return 1
            return 2

    class InterfaceMetadataList(BaseModel):
        interface_metadata: list = Field(default_factory=list)

    class NetworkDevicesMetadata(BaseModel):
        namespace: str = None
        devices: Optional[list[DeviceMetadata]] = Field(default_factory=list)
        interfaces: Optional[list[InterfaceMetadata]] = Field(default_factory=list)
        collect_timestamp: Optional[float] = None
