# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Union

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class ObfuscatorOptions(BaseModel):
    class Config:
        allow_mutation = False

    replace_digits: Optional[bool]


class QueryActivity(BaseModel):
    class Config:
        allow_mutation = False

    collection_interval: Optional[float]
    enabled: Optional[bool]
    max_active_rows: Optional[float]


class QueryMetrics(BaseModel):
    class Config:
        allow_mutation = False

    collection_interval: Optional[float]
    enabled: Optional[bool]


class QuerySamples(BaseModel):
    class Config:
        allow_mutation = False

    collection_interval: Optional[float]
    enabled: Optional[bool]
    explain_function: Optional[str]
    explained_queries_cache_maxsize: Optional[int]
    explained_queries_per_hour_per_query: Optional[int]
    samples_per_hour_per_query: Optional[int]
    seen_samples_cache_maxsize: Optional[int]


class Relation(BaseModel):
    class Config:
        allow_mutation = False

    relation_name: Optional[str]
    relation_regex: Optional[str]
    relation_schema: Optional[str]
    relkind: Optional[Sequence[str]]
    schemas: Optional[Sequence[str]]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    application_name: Optional[str]
    collect_activity_metrics: Optional[bool]
    collect_count_metrics: Optional[bool]
    collect_database_size_metrics: Optional[bool]
    collect_default_database: Optional[bool]
    collect_function_metrics: Optional[bool]
    collect_wal_metrics: Optional[bool]
    custom_queries: Optional[Sequence[Mapping[str, Any]]]
    data_directory: Optional[str]
    dbm: Optional[bool]
    dbname: Optional[str]
    dbstrict: Optional[bool]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: Optional[bool]
    host: str
    ignore_databases: Optional[Sequence[str]]
    max_relations: Optional[int]
    min_collection_interval: Optional[float]
    obfuscator_options: Optional[ObfuscatorOptions]
    password: Optional[str]
    pg_stat_statements_view: Optional[str]
    port: Optional[int]
    query_activity: Optional[QueryActivity]
    query_metrics: Optional[QueryMetrics]
    query_samples: Optional[QuerySamples]
    query_timeout: Optional[int]
    relations: Optional[Sequence[Union[str, Relation]]]
    service: Optional[str]
    ssl: Optional[str]
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
