# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pydantic import BaseModel, Field, computed_field

class NodeAttributes(BaseModel):
    address: str | None = None
    adSt: str | None = None
    role: str | None = None
    dn: str | None = None
    model: str | None = None
    version: str | None = None
    serial: str | None = None
    vendor: str | None = Field(default='cisco_aci')
    namespace: str | None = Field(default='default')

class Node(BaseModel):
    attributes: NodeAttributes

class DeviceMetadata(BaseModel):
    device_id: str | None = Field(default=None)
    id_tags: list = Field(default_factory=list)
    tags: list = Field(default_factory=list)
    name: str | None = Field(default=None) 
    ip_address: str | None = Field(default=None)
    model: str | None = Field(default=None)
    adSt: str | None = Field(default=None, exclude=True)
    vendor: str | None = Field(default=None)
    version: str | None = Field(default=None)
    serial_number: str | None = Field(default=None)

    @computed_field
    @property
    def status(self) -> int:
        return 1 if self.adSt=='on' else 2

class DeviceMetadataList(BaseModel):
    device_metadata: list = Field(default_factory=list)