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

    account: str
    authenticator: Optional[str]
    client_prefetch_threads: Optional[int]
    client_session_keep_alive: Optional[bool]
    custom_queries: Optional[Sequence[CustomQuery]]
    database: Optional[str]
    empty_default_hostname: Optional[bool]
    login_timeout: Optional[int]
    metric_groups: Optional[Sequence[str]]
    min_collection_interval: Optional[float]
    ocsp_response_cache_filename: Optional[str]
    password: str
    role: str
    schema: Optional[str]
    service: Optional[str]
    tags: Optional[Sequence[str]]
    token: Optional[str]
    use_global_custom_queries: Optional[str]
    user: str
    warehouse: Optional[str]

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
