{license_header}

{documentation}

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class SharedConfig(BaseModel):
    model_config = ConfigDict(
        validate_default=True,
        arbitrary_types_allowed=True,
        frozen=True,
    )
    collect_default_metrics: bool
    conf: Optional[tuple[MappingProxyType[str, Any], ...]] = None
    is_jmx: bool
    new_gc_metrics: Optional[bool] = None
    service: Optional[str] = None
    service_check_prefix: Optional[str] = None

    @model_validator(mode='before')
    def _initial_validation(cls, values):
        return validation.core.initialize_config(getattr(validators, 'initialize_shared', identity)(values))

    @field_validator('*', mode='before')
    def _validate(cls, value, info):
        field = cls.model_fields[info.field_name]
        field_name = field.alias or info.field_name
        if field_name in info.context['configured_fields']:
            value = getattr(validators, f'shared_{{info.field_name}}', identity)(value, field=field)
        else:
            value = getattr(defaults, f'shared_{{info.field_name}}', lambda: value)()

        return validation.utils.make_immutable(value)

    @model_validator(mode='after')
    def _final_validation(cls, model):
        return validation.core.check_model(getattr(validators, 'check_shared', identity)(model))
