# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    countonly: Optional[bool]
    directory: str
    dirs_patterns_full: Optional[bool]
    dirtagname: Optional[str]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: Optional[bool]
    exclude_dirs: Optional[Sequence[str]]
    filegauges: Optional[bool]
    filetagname: Optional[str]
    follow_symlinks: Optional[bool]
    ignore_missing: Optional[bool]
    min_collection_interval: Optional[float]
    name: Optional[str]
    pattern: Optional[str]
    recursive: Optional[bool]
    service: Optional[str]
    stat_follow_symlinks: Optional[bool]
    submit_histograms: Optional[bool]
    tags: Optional[Sequence[str]]

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
