# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pydantic import BaseModel, Field, computed_field


class NodeAttributes(BaseModel):
    address: str | None = None
    ad_st: str | None = Field(default=None, alias="adSt")
    role: str | None = None
    dn: str | None = None
    model: str | None = None
    version: str | None = None
    serial: str | None = None
    vendor: str | None = Field(default='cisco_aci')
    namespace: str | None = Field(default='default')


class Node(BaseModel):
    attributes: NodeAttributes


class EthAttributes(BaseModel):
    admin_st: str | None = Field(default=None, alias="adminSt")
    id: str | None = None
    name: str | None = None
    desc: str | None = None
    router_mac: str | None = Field(default=None, alias="routerMac")


class Eth(BaseModel):
    attributes: EthAttributes


class DeviceMetadata(BaseModel):
    device_id: str | None = Field(default=None)
    id_tags: list = Field(default_factory=list)
    tags: list = Field(default_factory=list)
    name: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    model: str | None = Field(default=None)
    ad_st: str | None = Field(default=None, exclude=True)
    vendor: str | None = Field(default=None)
    version: str | None = Field(default=None)
    serial_number: str | None = Field(default=None)

    @computed_field
    @property
    def status(self) -> int:
        return 1 if self.ad_st == 'on' else 2


class DeviceMetadataList(BaseModel):
    device_metadata: list = Field(default_factory=list)


class InterfaceMetadata(BaseModel):
    device_id: str | None = Field(default=None)
    id_tags: list = Field(default_factory=list)
    index: str | None = Field(default=None)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    mac_address: str | None = Field(default=None)
    admin_status: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def status(self) -> int:
        return 1 if self.admin_status == 'up' else 2


class InterfaceMetadataList(BaseModel):
    interface_metadata: list = Field(default_factory=list)
