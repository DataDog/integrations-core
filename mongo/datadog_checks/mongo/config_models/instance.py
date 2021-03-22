# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, deprecations, validators


class Fields(BaseModel):
    class Config:
        allow_mutation = False

    field_name: Optional[str]
    name: Optional[str]
    type: Optional[str]


class CustomQuery(BaseModel):
    class Config:
        allow_mutation = False

    database: Optional[str]
    fields: Optional[Fields]
    metric_prefix: Optional[str]
    query: Optional[str]
    tags: Optional[Sequence[str]]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    additional_metrics: Optional[Sequence[str]]
    collections: Optional[Sequence[str]]
    collections_indexes_stats: Optional[bool]
    connection_scheme: Optional[str]
    custom_queries: Optional[Sequence[CustomQuery]]
    database: Optional[str]
    empty_default_hostname: Optional[bool]
    hosts: Sequence[str]
    min_collection_interval: Optional[float]
    options: Optional[Mapping[str, Any]]
    password: Optional[str]
    replica_check: Optional[bool]
    server: Optional[str]
    service: Optional[str]
    ssl: Optional[bool]
    ssl_ca_certs: Optional[str]
    ssl_cert_reqs: Optional[int]
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    tags: Optional[Sequence[str]]
    timeout: Optional[int]
    username: Optional[str]

    @root_validator(pre=True)
    def _handle_deprecations(cls, values):
        validation.utils.handle_deprecations('instances', deprecations.instance(), values)
        return values

    @root_validator(pre=True)
    def _initial_validation(cls, values):
        return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

    @validator('*', pre=True, always=True)
    def _ensure_defaults(cls, v, field):
        if v is not None or field.required:
            return v

        return getattr(defaults, f'instance_{field.name}')(field, v)

    @validator('*')
    def _run_validations(cls, v, field):
        if not v:
            return v

        return getattr(validators, f'instance_{field.name}', identity)(v, field=field)

    @root_validator(pre=False)
    def _final_validation(cls, values):
        return validation.core.finalize_config(getattr(validators, 'finalize_instance', identity)(values))
