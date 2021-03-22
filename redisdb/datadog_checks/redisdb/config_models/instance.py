# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Optional, Sequence

from pydantic import BaseModel, Field, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    collect_client_metrics: Optional[bool]
    command_stats: Optional[bool]
    db: Optional[int]
    disable_connection_cache: Optional[bool]
    empty_default_hostname: Optional[bool]
    host: str
    keys: Optional[Sequence[str]]
    min_collection_interval: Optional[float]
    password: Optional[str]
    port: int
    service: Optional[str]
    slowlog_max_len: Optional[int] = Field(None, alias='slowlog-max-len')
    socket_timeout: Optional[int]
    ssl: Optional[bool]
    ssl_ca_certs: Optional[str]
    ssl_cert_reqs: Optional[int]
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    tags: Optional[Sequence[str]]
    unix_socket_path: Optional[str]
    username: Optional[str]
    warn_on_missing_keys: Optional[bool]

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
