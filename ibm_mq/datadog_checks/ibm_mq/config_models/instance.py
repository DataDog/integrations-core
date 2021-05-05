# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    auto_discover_queues: Optional[bool]
    channel: str
    channel_status_mapping: Optional[Mapping[str, Any]]
    channels: Optional[Sequence[str]]
    collect_statistics_metrics: Optional[bool]
    connection_name: Optional[str]
    convert_endianness: Optional[bool]
    empty_default_hostname: Optional[bool]
    host: Optional[str]
    min_collection_interval: Optional[float]
    mqcd_version: Optional[float]
    password: Optional[str]
    port: Optional[int]
    queue_manager: str
    queue_patterns: Optional[Sequence[str]]
    queue_regex: Optional[Sequence[str]]
    queue_tag_re: Optional[Mapping[str, Any]]
    queues: Optional[Sequence[str]]
    service: Optional[str]
    ssl_auth: Optional[bool]
    ssl_certificate_label: Optional[str]
    ssl_cipher_spec: Optional[str]
    ssl_key_repository_location: Optional[str]
    tags: Optional[Sequence[str]]
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
