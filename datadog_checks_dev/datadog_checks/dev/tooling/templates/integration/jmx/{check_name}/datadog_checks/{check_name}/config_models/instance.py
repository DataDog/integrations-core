{license_header}

{documentation}

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    model_config = ConfigDict(
        validate_default=True,
        arbitrary_types_allowed=True,
        frozen=True,
    )
    collect_default_jvm_metrics: Optional[bool] = None
    empty_default_hostname: Optional[bool] = None
    host: str
    java_bin_path: Optional[str] = None
    java_options: Optional[str] = None
    jmx_url: Optional[str] = None
    key_store_password: Optional[str] = None
    key_store_path: Optional[str] = None
    min_collection_interval: Optional[float] = None
    name: Optional[str] = None
    password: Optional[str] = None
    port: int
    process_name_regex: Optional[str] = None
    rmi_client_timeout: Optional[float] = None
    rmi_connection_timeout: Optional[float] = None
    rmi_registry_ssl: Optional[bool] = None
    service: Optional[str] = None
    tags: Optional[tuple[str, ...]] = None
    tools_jar_path: Optional[str] = None
    trust_store_password: Optional[str] = None
    trust_store_path: Optional[str] = None
    user: Optional[str] = None

    @model_validator(mode='before')
    def _initial_validation(cls, values):
        return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

    @field_validator('*', mode='before')
    def _validate(cls, value, info):
        field = cls.model_fields[info.field_name]
        field_name = field.alias or info.field_name
        if field_name in info.context['configured_fields']:
            value = getattr(validators, f'instance_{{info.field_name}}', identity)(value, field=field)
        else:
            value = getattr(defaults, f'instance_{{info.field_name}}', lambda: value)()

        return validation.utils.make_immutable(value)

    @model_validator(mode='after')
    def _final_validation(cls, model):
        return validation.core.check_model(getattr(validators, 'check_instance', identity)(model))
