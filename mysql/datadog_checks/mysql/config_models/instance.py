# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class CustomQuery(BaseModel):
    class Config:
        allow_mutation = False

    columns: Optional[Sequence[Mapping[str, Any]]]
    query: Optional[str]
    tags: Optional[Sequence[str]]


class Options(BaseModel):
    class Config:
        allow_mutation = False

    disable_innodb_metrics: Optional[bool]
    extra_innodb_metrics: Optional[bool]
    extra_performance_metrics: Optional[bool]
    extra_status_metrics: Optional[bool]
    galera_cluster: Optional[bool]
    replication: Optional[bool]
    replication_channel: Optional[str]
    replication_non_blocking_status: Optional[bool]
    schema_size_metrics: Optional[bool]


class Ssl(BaseModel):
    class Config:
        allow_mutation = False

    ca: Optional[str]
    cert: Optional[str]
    key: Optional[str]


class StatementSamples(BaseModel):
    class Config:
        allow_mutation = False

    collection_strategy_cache_maxsize: Optional[int]
    collection_strategy_cache_ttl: Optional[int]
    collections_per_second: Optional[float]
    enabled: Optional[bool]
    events_statements_enable_procedure: Optional[str]
    events_statements_row_limit: Optional[int]
    events_statements_table: Optional[str]
    events_statements_temp_table_name: Optional[str]
    explain_procedure: Optional[str]
    explained_statements_cache_maxsize: Optional[int]
    explained_statements_per_hour_per_query: Optional[int]
    fully_qualified_explain_procedure: Optional[str]
    samples_per_hour_per_query: Optional[int]
    seen_samples_cache_maxsize: Optional[int]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    charset: Optional[str]
    connect_timeout: Optional[float]
    custom_queries: Optional[Sequence[CustomQuery]]
    deep_database_monitoring: Optional[bool]
    defaults_file: Optional[str]
    empty_default_hostname: Optional[bool]
    host: Optional[str]
    max_custom_queries: Optional[int]
    min_collection_interval: Optional[float]
    options: Optional[Options]
    pass_: Optional[str] = Field(None, alias='pass')
    port: Optional[float]
    queries: Optional[Sequence[Mapping[str, Any]]]
    service: Optional[str]
    sock: Optional[str]
    ssl: Optional[Ssl]
    statement_metrics_limits: Optional[Mapping[str, Any]]
    statement_samples: Optional[StatementSamples]
    tags: Optional[Sequence[str]]
    use_global_custom_queries: Optional[str]
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
