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

    adoprovider: Optional[str]
    ao_database: Optional[str]
    autodiscovery_exclude: Optional[Sequence[str]]
    autodiscovery_include: Optional[Sequence[str]]
    availability_group: Optional[str]
    command_timeout: Optional[int]
    connection_string: Optional[str]
    connector: Optional[str]
    custom_queries: Optional[Sequence[CustomQuery]]
    database: Optional[str]
    database_autodiscovery: Optional[bool]
    database_autodiscovery_interval: Optional[int]
    db_fragmentation_object_names: Optional[Sequence[str]]
    driver: Optional[str]
    dsn: Optional[str]
    empty_default_hostname: Optional[bool]
    host: str
    ignore_missing_database: Optional[bool]
    include_ao_metrics: Optional[bool]
    include_db_fragmentation_metrics: Optional[bool]
    include_fci_metrics: Optional[bool]
    include_instance_metrics: Optional[bool]
    include_task_scheduler_metrics: Optional[bool]
    min_collection_interval: Optional[float]
    only_emit_local: Optional[bool]
    password: Optional[str]
    proc_only_if: Optional[str]
    proc_only_if_database: Optional[str]
    service: Optional[str]
    stored_procedure: Optional[str]
    tags: Optional[Sequence[str]]
    use_global_custom_queries: Optional[str]
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
