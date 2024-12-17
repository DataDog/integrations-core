# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from enum import IntEnum, StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from . import helpers

"""
Cisco ACI Response Models
"""


class NodeAttributes(BaseModel):
    address: Optional[str] = None
    ad_st: Optional[str] = Field(default=None, alias="adSt")
    fabric_st: Optional[str] = Field(default=None, alias="fabricSt")
    role: Optional[str] = None
    dn: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    serial: Optional[str] = None
    vendor: Optional[str] = Field(default='cisco')
    namespace: Optional[str] = Field(default='default')

    @computed_field
    @property
    def device_type(self) -> str:
        if self.role in ['leaf', 'spine']:
            return 'switch'
        return 'other'

    @computed_field
    @property
    def status(self) -> int:
        if self.role == 'controller':
            return 1 if self.ad_st == 'on' else 2
        mapping = {
            'active': 1,
            'inactive': 2,
            'disabled': 2,
            'discovering': 2,
            'undiscovered': 2,
            'unsupported': 2,
            'unknown': 2,
        }
        return mapping.get(self.fabric_st, 2)


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

    @model_validator(mode='before')
    @classmethod
    def validate_name(cls, data: dict) -> dict:
        if isinstance(data, dict):
            name = data.get('name')
            id = data.get('id')
            if not name or name == '':
                data['name'] = id
        return data


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


class LldpAdjAttributes(BaseModel):
    chassis_id_t: Optional[str] = Field(default=None, alias="chassisIdT")
    chassis_id_v: Optional[str] = Field(default=None, alias="chassisIdV")
    dn: Optional[str] = None
    mgmt_ip: Optional[str] = Field(default=None, alias="mgmtIp")
    mgmt_port_mac: Optional[str] = Field(default=None, alias="mgmtPortMac")
    port_desc: Optional[str] = Field(default=None, alias="portDesc")
    port_id_t: Optional[str] = Field(default=None, alias="portIdT")
    port_id_v: Optional[str] = Field(default=None, alias="portIdV")
    sys_desc: Optional[str] = Field(default=None, alias="sysDesc")
    sys_name: Optional[str] = Field(default=None, alias="sysName")

    @computed_field
    @property
    def ndm_remote_interface_type(self) -> str:
        # map the Cisco ACI port subtype to match what NDM (writer) expects
        port_subtype_mapping = {
            "if-alias": "interface_alias",
            "port-name": "interface_name",
            "mac": "mac_address",
            "nw-addr": "network_address",
            "if-name": "interface_name",
            "agent-ckt-id": "agent_circuit_id",
            "local": "local",
        }
        if self.port_id_t:
            return port_subtype_mapping.get(self.port_id_t, "unknown")
        return "unknown"

    @computed_field
    @property
    def local_device_dn(self) -> str:
        # example: topology/pod-1/node-101/sys/lldp/inst/if-[eth1/49]/adj-1
        return helpers.get_hostname_from_dn(self.dn)

    @computed_field
    @property
    def local_port_id(self) -> str:
        # example: topology/pod-1/paths-201/path-ep-[eth1/1]
        # use regex to extract port alias from square brackets - ex: eth1/1
        return helpers.get_eth_id_from_dn(self.dn)

    @computed_field
    @property
    def local_port_index(self) -> int:
        return helpers.get_index_from_eth_id(self.local_port_id)

    @computed_field
    @property
    def remote_device_dn(self) -> str:
        # example: topology/pod-1/paths-201/path-ep-[eth1/1]
        # use regex to extract the pod/node - ex: pod-1-node-201
        return helpers.get_hostname_from_dn(self.sys_desc)

    @computed_field
    @property
    def remote_port_id(self) -> str:
        # example: topology/pod-1/paths-201/path-ep-[eth1/1]
        # use regex to extract port alias from square brackets - ex: eth1/1
        return helpers.get_eth_id_from_dn(self.port_desc)

    @computed_field
    @property
    def remote_port_index(self) -> int:
        return helpers.get_index_from_eth_id(self.remote_port_id)


class LldpAdjEp(BaseModel):
    attributes: LldpAdjAttributes


"""
NDM Models
"""


class DeviceMetadata(BaseModel):
    id: Optional[str] = Field(default=None)
    id_tags: list = Field(default_factory=list)
    tags: list = Field(default_factory=list)
    name: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    status: Optional[int] = Field(default=None)
    model: Optional[str] = Field(default=None)
    vendor: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    serial_number: Optional[str] = Field(default=None)
    device_type: Optional[str] = Field(default=None)
    integration: Optional[str] = Field(default='cisco-aci')

    # non-exported fields
    pod_node_id: Optional[str] = Field(default=None, exclude=True)


class DeviceMetadataList(BaseModel):
    device_metadata: list = Field(default_factory=list)


class AdminStatus(IntEnum):
    UP = 1
    DOWN = 2


class OperStatus(IntEnum):
    UP = 1
    DOWN = 2


class Status(StrEnum):
    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    OFF = "off"


class InterfaceMetadata(BaseModel):
    device_id: Optional[str] = Field(default=None)
    id_tags: list = Field(default_factory=list)
    raw_id: Optional[str] = Field(default=None)
    raw_id_type: Optional[str] = Field(default='cisco-aci')
    index: Optional[int] = Field(default=None)
    name: Optional[str] = Field(default=None)
    alias: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    mac_address: Optional[str] = Field(default=None)
    admin_status: Optional[AdminStatus] = Field(default=None)
    oper_status: Optional[OperStatus] = Field(default=None)
    integration: Optional[str] = Field(default='cisco-aci')

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    @field_validator("admin_status", mode="before")
    @classmethod
    def parse_admin_status(cls, admin_status: AdminStatus | None) -> AdminStatus | None:
        if not admin_status:
            return None
        if admin_status == "up" or admin_status == 1:
            return AdminStatus.UP
        return AdminStatus.DOWN

    @field_validator("oper_status", mode="before")
    @classmethod
    def parse_oper_status(cls, oper_status: OperStatus | None) -> OperStatus | None:
        if not oper_status:
            return None
        if oper_status == "up" or oper_status == 1:
            return OperStatus.UP
        return OperStatus.DOWN

    @field_validator("index", mode="before")
    @classmethod
    def parse_index(cls, index: str | int | None) -> int | None:
        if type(index) == str:
            split = re.split('eth|/', index)
            return int(split[-1])
        if type(index) == int:
            return index
        return None

    @computed_field
    @property
    def status(self) -> Status:
        if self.admin_status == AdminStatus.UP:
            if self.oper_status == OperStatus.UP:
                return Status.UP
            if self.oper_status == OperStatus.DOWN:
                return Status.DOWN
            return Status.WARNING
        if self.admin_status == AdminStatus.DOWN:
            if self.oper_status == OperStatus.UP:
                return Status.DOWN
            if self.oper_status == OperStatus.DOWN:
                return Status.OFF
            return Status.WARNING
        return Status.DOWN


class InterfaceMetadataList(BaseModel):
    interface_metadata: list = Field(default_factory=list)


class TopologyLinkDevice(BaseModel):
    dd_id: Optional[str] = None
    id: Optional[str] = None
    id_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None


class TopologyLinkInterface(BaseModel):
    dd_id: Optional[str] = None
    id: Optional[str] = None
    id_type: Optional[str] = None
    description: Optional[str] = None


class TopologyLinkSide(BaseModel):
    device: Optional[TopologyLinkDevice] = None
    interface: Optional[TopologyLinkInterface] = None


class SourceType(StrEnum):
    LLDP = "lldp"
    CDP = "cdp"
    OTHER = "OTHER"


class TopologyLinkMetadata(BaseModel):
    id: Optional[str] = None
    source_type: Optional[SourceType] = Field(default=None)
    local: Optional[TopologyLinkSide] = Field(default=None)
    remote: Optional[TopologyLinkSide] = Field(default=None)
    integration: Optional[str] = Field(default='cisco-aci')


class NetworkDevicesMetadata(BaseModel):
    namespace: str = None
    devices: Optional[list[DeviceMetadata]] = Field(default_factory=list)
    interfaces: Optional[list[InterfaceMetadata]] = Field(default_factory=list)
    links: Optional[list[TopologyLinkMetadata]] = Field(default_factory=list)
    collect_timestamp: Optional[int] = None
    size: Optional[int] = Field(default=0, exclude=True)

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    def append_metadata(self, metadata: DeviceMetadata | InterfaceMetadata):
        if isinstance(metadata, DeviceMetadata):
            self.devices.append(metadata)
        if isinstance(metadata, InterfaceMetadata):
            self.interfaces.append(metadata)
        if isinstance(metadata, TopologyLinkMetadata):
            self.links.append(metadata)
        self.size += 1
