# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class CollectPerInstanceFilters(BaseModel):
    class Config:
        allow_mutation = False

    cluster: Optional[Sequence[str]]
    datastore: Optional[Sequence[str]]
    host: Optional[Sequence[str]]
    vm: Optional[Sequence[str]]


class MetricFilters(BaseModel):
    class Config:
        allow_mutation = False

    cluster: Optional[Sequence[str]]
    datacenter: Optional[Sequence[str]]
    datastore: Optional[Sequence[str]]
    host: Optional[Sequence[str]]
    vm: Optional[Sequence[str]]


class ResourceFilter(BaseModel):
    class Config:
        allow_mutation = False

    patterns: Optional[Sequence[str]]
    property: Optional[str]
    resource: Optional[str]
    type: Optional[str]


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


class RestApiOptions(BaseModel):
    class Config:
        allow_mutation = False

    allow_redirects: Optional[bool]
    auth_token: Optional[AuthToken]
    auth_type: Optional[str]
    aws_host: Optional[str]
    aws_region: Optional[str]
    aws_service: Optional[str]
    connect_timeout: Optional[float]
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
    ntlm_domain: Optional[str]
    password: Optional[str]
    persist_connections: Optional[bool]
    proxy: Optional[Proxy]
    read_timeout: Optional[float]
    request_size: Optional[float]
    skip_proxy: Optional[bool]
    timeout: Optional[float]
    tls_ca_cert: Optional[str]
    tls_cert: Optional[str]
    tls_ignore_warning: Optional[bool]
    tls_private_key: Optional[str]
    tls_use_host_header: Optional[bool]
    tls_verify: Optional[bool]
    use_legacy_auth_encoding: Optional[bool]
    username: Optional[str]


class InstanceConfig(BaseModel):
    class Config:
        allow_mutation = False

    attributes_prefix: Optional[str]
    batch_property_collector_size: Optional[int]
    batch_tags_collector_size: Optional[int]
    collect_attributes: Optional[bool]
    collect_events: Optional[bool]
    collect_events_only: Optional[bool]
    collect_per_instance_filters: Optional[CollectPerInstanceFilters]
    collect_tags: Optional[bool]
    collection_level: Optional[int]
    collection_type: Optional[str]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: bool
    excluded_host_tags: Optional[Sequence[str]]
    host: str
    include_datastore_cluster_folder_tag: Optional[bool]
    max_historical_metrics: Optional[int]
    metric_filters: Optional[MetricFilters]
    metrics_per_query: Optional[int]
    min_collection_interval: Optional[float]
    password: str
    refresh_infrastructure_cache_interval: Optional[int]
    refresh_metrics_metadata_cache_interval: Optional[int]
    resource_filters: Optional[Sequence[ResourceFilter]]
    rest_api_options: Optional[RestApiOptions]
    service: Optional[str]
    ssl_capath: Optional[str]
    ssl_verify: Optional[bool]
    tags: Optional[Sequence[str]]
    tags_prefix: Optional[str]
    threads_count: Optional[int]
    tls_ignore_warning: Optional[bool]
    use_collect_events_fallback: Optional[bool]
    use_guest_hostname: Optional[bool]
    use_legacy_check_version: bool
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
