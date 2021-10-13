# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_proxy(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_skip_proxy(field, value):
    return False


def shared_timeout(field, value):
    return 10


def instance_allow_redirects(field, value):
    return True


def instance_auth_token(field, value):
    return get_default_field_value(field, value)


def instance_auth_type(field, value):
    return 'basic'


def instance_aws_host(field, value):
    return get_default_field_value(field, value)


def instance_aws_region(field, value):
    return get_default_field_value(field, value)


def instance_aws_service(field, value):
    return get_default_field_value(field, value)


def instance_cache_metric_wildcards(field, value):
    return True


def instance_cache_shared_labels(field, value):
    return True


def instance_collect_counters_with_distributions(field, value):
    return False


def instance_collect_histogram_buckets(field, value):
    return True


def instance_connect_timeout(field, value):
    return get_default_field_value(field, value)


def instance_disable_generic_tags(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_enable_health_service_check(field, value):
    return True


def instance_exclude_labels(field, value):
    return get_default_field_value(field, value)


def instance_exclude_metrics(field, value):
    return get_default_field_value(field, value)


def instance_exclude_metrics_by_labels(field, value):
    return get_default_field_value(field, value)


def instance_extra_headers(field, value):
    return get_default_field_value(field, value)


def instance_extra_metrics(field, value):
    return get_default_field_value(field, value)


def instance_headers(field, value):
    return get_default_field_value(field, value)


def instance_histogram_buckets_as_distributions(field, value):
    return False


def instance_hostname_format(field, value):
    return get_default_field_value(field, value)


def instance_hostname_label(field, value):
    return get_default_field_value(field, value)


def instance_ignore_tags(field, value):
    return get_default_field_value(field, value)


def instance_istio_mesh_endpoint(field, value):
    return get_default_field_value(field, value)


def instance_istiod_endpoint(field, value):
    return get_default_field_value(field, value)


def instance_kerberos_auth(field, value):
    return 'disabled'


def instance_kerberos_cache(field, value):
    return get_default_field_value(field, value)


def instance_kerberos_delegate(field, value):
    return False


def instance_kerberos_force_initiate(field, value):
    return False


def instance_kerberos_hostname(field, value):
    return get_default_field_value(field, value)


def instance_kerberos_keytab(field, value):
    return get_default_field_value(field, value)


def instance_kerberos_principal(field, value):
    return get_default_field_value(field, value)


def instance_log_requests(field, value):
    return False


def instance_metrics(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_namespace(field, value):
    return get_default_field_value(field, value)


def instance_non_cumulative_histogram_buckets(field, value):
    return False


def instance_ntlm_domain(field, value):
    return get_default_field_value(field, value)


def instance_openmetrics_endpoint(field, value):
    return get_default_field_value(field, value)


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_persist_connections(field, value):
    return False


def instance_proxy(field, value):
    return get_default_field_value(field, value)


def instance_raw_line_filters(field, value):
    return get_default_field_value(field, value)


def instance_raw_metric_prefix(field, value):
    return get_default_field_value(field, value)


def instance_read_timeout(field, value):
    return get_default_field_value(field, value)


def instance_rename_labels(field, value):
    return get_default_field_value(field, value)


def instance_request_size(field, value):
    return 16


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_share_labels(field, value):
    return get_default_field_value(field, value)


def instance_skip_proxy(field, value):
    return False


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_telemetry(field, value):
    return False


def instance_timeout(field, value):
    return 10


def instance_tls_ca_cert(field, value):
    return get_default_field_value(field, value)


def instance_tls_cert(field, value):
    return get_default_field_value(field, value)


def instance_tls_ignore_warning(field, value):
    return False


def instance_tls_private_key(field, value):
    return get_default_field_value(field, value)


def instance_tls_use_host_header(field, value):
    return False


def instance_tls_verify(field, value):
    return True


def instance_use_latest_spec(field, value):
    return False


def instance_use_legacy_auth_encoding(field, value):
    return True


def instance_use_openmetrics(field, value):
    return True


def instance_username(field, value):
    return get_default_field_value(field, value)
