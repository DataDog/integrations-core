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


class Components(BaseModel):
    class Config:
        allow_mutation = False

    exclude: Optional[Sequence[str]]
    include: Optional[Sequence[str]]
    tag: Optional[str]


class Proxy(BaseModel):
    class Config:
        allow_mutation = False

    http: Optional[str]
    https: Optional[str]
    no_proxy: Optional[Sequence[str]]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    allow_redirects: Optional[bool]
    auth_token: Optional[AuthToken]
    auth_type: Optional[str]
    aws_host: Optional[str]
    aws_region: Optional[str]
    aws_service: Optional[str]
    collect_default_jvm_metrics: Optional[bool]
    components: Optional[Components]
    connect_timeout: Optional[float]
    default_exclude: Optional[Sequence[str]]
    default_include: Optional[Sequence[str]]
    default_tag: Optional[str]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: Optional[bool]
    extra_headers: Optional[Mapping[str, Any]]
    headers: Optional[Mapping[str, Any]]
    host: Optional[str]
    is_jmx: Optional[bool]
    java_bin_path: Optional[str]
    java_options: Optional[str]
    jmx_url: Optional[str]
    kerberos_auth: Optional[str]
    kerberos_cache: Optional[str]
    kerberos_delegate: Optional[bool]
    kerberos_force_initiate: Optional[bool]
    kerberos_hostname: Optional[str]
    kerberos_keytab: Optional[str]
    kerberos_principal: Optional[str]
    key_store_password: Optional[str]
    key_store_path: Optional[str]
    log_requests: Optional[bool]
    min_collection_interval: Optional[float]
    name: Optional[str]
    ntlm_domain: Optional[str]
    password: Optional[str]
    persist_connections: Optional[bool]
    port: Optional[int]
    process_name_regex: Optional[str]
    proxy: Optional[Proxy]
    read_timeout: Optional[float]
    request_size: Optional[float]
    rmi_client_timeout: Optional[float]
    rmi_connection_timeout: Optional[float]
    rmi_registry_ssl: Optional[bool]
    service: Optional[str]
    skip_proxy: Optional[bool]
    tags: Optional[Sequence[str]]
    timeout: Optional[float]
    tls_ca_cert: Optional[str]
    tls_cert: Optional[str]
    tls_ignore_warning: Optional[bool]
    tls_private_key: Optional[str]
    tls_use_host_header: Optional[bool]
    tls_verify: Optional[bool]
    tools_jar_path: Optional[str]
    trust_store_password: Optional[str]
    trust_store_path: Optional[str]
    use_legacy_auth_encoding: Optional[bool]
    user: Optional[str]
    username: Optional[str]
    web_endpoint: Optional[str]

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
