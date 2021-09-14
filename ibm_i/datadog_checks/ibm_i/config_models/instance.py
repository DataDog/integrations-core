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

    connection_string: Optional[str]
    disable_generic_tags: Optional[bool]
    driver: Optional[str]
    empty_default_hostname: Optional[bool]
    job_query_timeout: Optional[int] = Field(None, gt=0.0)
    min_collection_interval: Optional[float]
    password: Optional[str]
    query_timeout: Optional[int] = Field(None, gt=0.0)
    service: Optional[str]
    severity_threshold: Optional[int] = Field(None, ge=0.0, le=99.0)
    system: Optional[str]
    system_mq_query_timeout: Optional[int] = Field(None, gt=0.0)
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
