# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Union

from pydantic import BaseModel, root_validator, validator

from datadog_checks.base.utils.functions import identity
from datadog_checks.base.utils.models import validation

from . import defaults, validators


class AuthToken(BaseModel):
    class Config:
        allow_mutation = False

    reader: Optional[Mapping[str, Any]]
    writer: Optional[Mapping[str, Any]]


class IgnoreMetricsByLabels(BaseModel):
    class Config:
        allow_mutation = False

    target_label_key: Optional[str]
    target_label_value_list: Optional[Sequence[str]]


class TargetMetric(BaseModel):
    class Config:
        allow_mutation = False

    label_to_match: Optional[str]
    labels_to_get: Optional[Sequence[str]]


class LabelJoins(BaseModel):
    class Config:
        allow_mutation = False

    target_metric: Optional[TargetMetric]


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
    bearer_token_auth: Optional[bool]
    bearer_token_path: Optional[str]
    connect_timeout: Optional[float]
    disable_generic_tags: Optional[bool]
    empty_default_hostname: Optional[bool]
    exclude_labels: Optional[Sequence[str]]
    extra_headers: Optional[Mapping[str, Any]]
    gitlab_url: str
    headers: Optional[Mapping[str, Any]]
    health_service_check: Optional[bool]
    ignore_metrics: Optional[Sequence[str]]
    ignore_metrics_by_labels: Optional[IgnoreMetricsByLabels]
    ignore_tags: Optional[Sequence[str]]
    kerberos_auth: Optional[str]
    kerberos_cache: Optional[str]
    kerberos_delegate: Optional[bool]
    kerberos_force_initiate: Optional[bool]
    kerberos_hostname: Optional[str]
    kerberos_keytab: Optional[str]
    kerberos_principal: Optional[str]
    label_joins: Optional[LabelJoins]
    label_to_hostname: Optional[str]
    labels_mapper: Optional[Mapping[str, Any]]
    log_requests: Optional[bool]
    metrics: Optional[Sequence[Union[str, Mapping[str, str]]]]
    min_collection_interval: Optional[float]
    namespace: Optional[str]
    ntlm_domain: Optional[str]
    password: Optional[str]
    persist_connections: Optional[bool]
    prometheus_endpoint: str
    prometheus_metrics_prefix: Optional[str]
    prometheus_url: str
    proxy: Optional[Proxy]
    read_timeout: Optional[float]
    request_size: Optional[float]
    send_distribution_buckets: Optional[bool]
    send_distribution_counts_as_monotonic: Optional[bool]
    send_distribution_sums_as_monotonic: Optional[bool]
    send_histograms_buckets: Optional[bool]
    send_monotonic_counter: Optional[bool]
    send_monotonic_with_gauge: Optional[bool]
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
    type_overrides: Optional[Mapping[str, Any]]
    use_legacy_auth_encoding: Optional[bool]
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
