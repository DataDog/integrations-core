# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class Relation(BaseModel):
    class Config:
        allow_mutation = False

    relation_name: Optional[str]
    relation_schema: Optional[str]
    schemas: Optional[Sequence[str]]


class StatementSamples(BaseModel):
    class Config:
        allow_mutation = False

    collections_per_second: Optional[float]
    enabled: Optional[bool]
    explain_function: Optional[str]
    explained_statements_cache_maxsize: Optional[int]
    explained_statements_per_hour_per_query: Optional[int]
    samples_per_hour_per_query: Optional[int]
    seen_samples_cache_maxsize: Optional[int]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    application_name: Optional[str]
    collect_activity_metrics: Optional[bool]
    collect_count_metrics: Optional[bool]
    collect_database_size_metrics: Optional[bool]
    collect_default_database: Optional[bool]
    collect_function_metrics: Optional[bool]
    custom_queries: Optional[Sequence[Mapping[str, Any]]]
    dbname: Optional[str]
    dbstrict: Optional[bool]
    deep_database_monitoring: Optional[bool]
    empty_default_hostname: Optional[bool]
    host: str
    max_relations: Optional[int]
    min_collection_interval: Optional[float]
    password: Optional[str]
    pg_stat_statements_view: Optional[str]
    port: Optional[int]
    query_timeout: Optional[int]
    relations: Optional[Sequence[Relation]]
    service: Optional[str]
    ssl: Optional[str]
    statement_metrics_limits: Optional[Mapping[str, Any]]
    statement_samples: Optional[StatementSamples]
    table_count_limit: Optional[int]
    tag_replication_role: Optional[bool]
    tags: Optional[Sequence[str]]
    username: str

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
