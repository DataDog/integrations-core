# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class AuthToken(BaseModel):
    class Config:
        allow_mutation = False

    reader: Optional[Mapping[str, Any]]
    writer: Optional[Mapping[str, Any]]


class Proxy(BaseModel):
    class Config:
        allow_mutation = False

    http: Optional[str]
    https: Optional[str]
    no_proxy: Optional[Sequence[str]]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    acl_token: Optional[str]
    allow_redirects: Optional[bool]
    auth_token: Optional[AuthToken]
    auth_type: Optional[str]
    aws_host: Optional[str]
    aws_region: Optional[str]
    aws_service: Optional[str]
    catalog_checks: Optional[bool]
    connect_timeout: Optional[float]
    disable_generic_tags: Optional[bool]
    disable_legacy_service_tag: Optional[bool]
    empty_default_hostname: Optional[bool]
    extra_headers: Optional[Mapping[str, Any]]
    headers: Optional[Mapping[str, Any]]
    kerberos_auth: Optional[str]
    kerberos_cache: Optional[str]
    kerberos_delegate: Optional[bool]
    kerberos_force_initiate: Optional[bool]
    kerberos_hostname: Optional[str]
    kerberos_keytab: Optional[str]
    kerberos_principal: Optional[str]
    log_requests: Optional[bool]
    max_services: Optional[float]
    min_collection_interval: Optional[float]
    network_latency_checks: Optional[bool]
    new_leader_checks: Optional[bool]
    ntlm_domain: Optional[str]
    password: Optional[str]
    persist_connections: Optional[bool]
    proxy: Optional[Proxy]
    read_timeout: Optional[float]
    request_size: Optional[float]
    self_leader_check: Optional[bool]
    service: Optional[str]
    services_exclude: Optional[Sequence[str]]
    services_include: Optional[Sequence[str]]
    single_node_install: Optional[bool]
    skip_proxy: Optional[bool]
    tags: Optional[Sequence[str]]
    threads_count: Optional[float]
    timeout: Optional[float]
    tls_ca_cert: Optional[str]
    tls_cert: Optional[str]
    tls_ignore_warning: Optional[bool]
    tls_private_key: Optional[str]
    tls_use_host_header: Optional[bool]
    tls_verify: Optional[bool]
    url: str
    use_legacy_auth_encoding: Optional[bool]
    use_prometheus_endpoint: Optional[bool]
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
