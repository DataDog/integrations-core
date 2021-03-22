# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    broker_requests_batch_size: Optional[int]
    consumer_groups: Optional[Mapping[str, Any]]
    empty_default_hostname: Optional[bool]
    kafka_client_api_version: Optional[str]
    kafka_connect_str: Sequence[str]
    kafka_consumer_offsets: Optional[bool]
    min_collection_interval: Optional[float]
    monitor_all_broker_highwatermarks: Optional[bool]
    monitor_unlisted_consumer_groups: Optional[bool]
    sasl_kerberos_domain_name: Optional[str]
    sasl_kerberos_service_name: Optional[str]
    sasl_mechanism: Optional[str]
    sasl_plain_password: Optional[str]
    sasl_plain_username: Optional[str]
    security_protocol: Optional[str]
    service: Optional[str]
    ssl_cafile: Optional[str]
    ssl_certfile: Optional[str]
    ssl_check_hostname: Optional[bool]
    ssl_context: Optional[str]
    ssl_crlfile: Optional[str]
    ssl_keyfile: Optional[str]
    ssl_password: Optional[str]
    tags: Optional[Sequence[str]]
    zk_connect_str: Optional[Sequence[Mapping[str, Any]]]
    zk_prefix: Optional[str]

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
