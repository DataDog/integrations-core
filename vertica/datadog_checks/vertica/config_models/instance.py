# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class CustomQuery(BaseModel):
    class Config:
        allow_mutation = False

    columns: Optional[Sequence[Mapping[str, Any]]]
    query: Optional[str]
    tags: Optional[Sequence[str]]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    backup_servers: Optional[Sequence[Mapping[str, Any]]]
    client_lib_log_level: Optional[str]
    connection_load_balance: Optional[bool]
    custom_queries: Optional[Sequence[CustomQuery]]
    db: Optional[str]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: Optional[bool]
    metric_groups: Optional[Sequence[str]]
    min_collection_interval: Optional[float]
    password: Optional[str]
    port: Optional[int]
    server: Optional[str]
    service: Optional[str]
    tags: Optional[Sequence[str]]
    timeout: Optional[int]
    tls_ca_cert: Optional[str]
    tls_cert: Optional[str]
    tls_private_key: Optional[str]
    tls_private_key_password: Optional[str]
    tls_validate_hostname: Optional[bool]
    tls_verify: Optional[bool]
    use_global_custom_queries: Optional[str]
    use_tls: Optional[bool]
    username: Optional[str]

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
