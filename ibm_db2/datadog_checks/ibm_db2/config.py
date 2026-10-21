# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import BeforeValidator, ConfigDict, Field, ValidationInfo, field_validator
from pydantic_core import PydanticUseDefault

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.containers import iter_unique

from .config_models import InstanceConfig, defaults
from .config_models.instance import QueryMetrics

CONFIG_MODELS_PACKAGE = 'datadog_checks.ibm_db2.config'

if TYPE_CHECKING:
    from .ibm_db2 import IbmDb2Check


def _use_default_if_none(value: object) -> object:
    if value is None:
        raise PydanticUseDefault()
    return value


class QueryMetricsConfig(QueryMetrics):
    """Apply the spec's nested defaults to empty YAML values as well as omitted fields."""

    model_config = ConfigDict(validate_default=True)

    @field_validator('*', mode='before')
    @classmethod
    def default_null_fields(cls, value: object, info: ValidationInfo) -> object:
        field = cls.model_fields[info.field_name]
        if not field.is_required() and field.default is not None:
            return _use_default_if_none(value)
        return value


class Db2Config(InstanceConfig):
    query_metrics: Annotated[QueryMetricsConfig, BeforeValidator(_use_default_if_none)] = Field(
        default_factory=QueryMetricsConfig
    )

    @field_validator('min_collection_interval', mode='before')
    @classmethod
    def default_collection_interval(cls, value: object) -> object:
        return defaults.instance_min_collection_interval() if value is None else value


def build_config(check: IbmDb2Check) -> Db2Config:
    """
    Build the typed instance configuration, folding `global_custom_queries` from `init_config` into
    `custom_queries` according to `use_global_custom_queries`.

    Raises `ConfigurationError` if the instance fails model validation.
    """
    instance = check.instance
    init_config = check.init_config
    args = dict(instance)
    custom_queries = list(instance.get('custom_queries', []))
    use_global_custom_queries = instance.get('use_global_custom_queries', True)
    if use_global_custom_queries == 'extend':
        custom_queries.extend(init_config.get('global_custom_queries', []))
    elif 'global_custom_queries' in init_config and is_affirmative(use_global_custom_queries):
        custom_queries = list(init_config.get('global_custom_queries', []))
    args['custom_queries'] = list(iter_unique(custom_queries))

    return check.load_configuration_model(
        CONFIG_MODELS_PACKAGE, 'Db2Config', args, check._get_config_model_context(args)
    )
