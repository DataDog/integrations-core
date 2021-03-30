{license_header}
from __future__ import annotations

from typing import Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    collect_default_jvm_metrics: Optional[bool]
    empty_default_hostname: Optional[bool]
    host: str
    java_bin_path: Optional[str]
    java_options: Optional[str]
    jmx_url: Optional[str]
    key_store_password: Optional[str]
    key_store_path: Optional[str]
    min_collection_interval: Optional[float]
    name: Optional[str]
    password: Optional[str]
    port: int
    process_name_regex: Optional[str]
    rmi_client_timeout: Optional[float]
    rmi_connection_timeout: Optional[float]
    rmi_registry_ssl: Optional[bool]
    service: Optional[str]
    tags: Optional[Sequence[str]]
    tools_jar_path: Optional[str]
    trust_store_password: Optional[str]
    trust_store_path: Optional[str]
    user: Optional[str]

    @root_validator(pre=True)
    def _initial_validation(cls, values):
        return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

    @validator('*', pre=True, always=True)
    def _ensure_defaults(cls, v, field):
        if v is not None or field.required:
            return v

        return getattr(defaults, f'instance_{{field.name}}')(field, v)

    @validator('*')
    def _run_validations(cls, v, field):
        if not v:
            return v

        return getattr(validators, f'instance_{{field.name}}', identity)(v, field=field)

    @root_validator(pre=False)
    def _final_validation(cls, values):
        return validation.core.finalize_config(getattr(validators, 'finalize_instance', identity)(values))
