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

    auth_type: Optional[str]
    bookmark_frequency: Optional[int]
    domain: Optional[str]
    empty_default_hostname: Optional[bool]
    event_format: Optional[Sequence[str]]
    event_id: Optional[Sequence[str]]
    event_priority: Optional[str]
    excluded_messages: Optional[Sequence[str]]
    filters: Optional[Mapping[str, Any]]
    host: Optional[str]
    included_messages: Optional[Sequence[str]]
    interpret_messages: Optional[bool]
    legacy_mode: Optional[bool]
    log_file: Optional[Sequence[str]]
    message_filters: Optional[Sequence[str]]
    min_collection_interval: Optional[float]
    password: Optional[str]
    path: Optional[str]
    payload_size: Optional[int]
    query: Optional[str]
    server: Optional[str]
    service: Optional[str]
    source_name: Optional[Sequence[str]]
    start: Optional[str]
    tag_event_id: Optional[bool]
    tag_sid: Optional[bool]
    tags: Optional[Sequence[str]]
    timeout: Optional[float]
    type: Optional[Sequence[str]]
    user: Optional[str]

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
