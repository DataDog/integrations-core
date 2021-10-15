# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_collect_default_metrics(field, value):
    return False


def shared_conf(field, value):
    return get_default_field_value(field, value)


def shared_is_jmx(field, value):
    return False


def shared_new_gc_metrics(field, value):
    return False


def shared_proxy(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_service_check_prefix(field, value):
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


def instance_collect_default_jvm_metrics(field, value):
    return True


def instance_components(field, value):
    return get_default_field_value(field, value)


def instance_connect_timeout(field, value):
    return get_default_field_value(field, value)


def instance_default_exclude(field, value):
    return get_default_field_value(field, value)


def instance_default_include(field, value):
    return get_default_field_value(field, value)


def instance_default_tag(field, value):
    return 'component'


def instance_disable_generic_tags(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_extra_headers(field, value):
    return get_default_field_value(field, value)


def instance_headers(field, value):
    return get_default_field_value(field, value)


def instance_host(field, value):
    return get_default_field_value(field, value)


def instance_is_jmx(field, value):
    return False


def instance_java_bin_path(field, value):
    return get_default_field_value(field, value)


def instance_java_options(field, value):
    return get_default_field_value(field, value)


def instance_jmx_url(field, value):
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


def instance_key_store_password(field, value):
    return get_default_field_value(field, value)


def instance_key_store_path(field, value):
    return get_default_field_value(field, value)


def instance_log_requests(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_name(field, value):
    return get_default_field_value(field, value)


def instance_ntlm_domain(field, value):
    return get_default_field_value(field, value)


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_persist_connections(field, value):
    return False


def instance_port(field, value):
    return get_default_field_value(field, value)


def instance_process_name_regex(field, value):
    return get_default_field_value(field, value)


def instance_proxy(field, value):
    return get_default_field_value(field, value)


def instance_read_timeout(field, value):
    return get_default_field_value(field, value)


def instance_request_size(field, value):
    return 16


def instance_rmi_client_timeout(field, value):
    return 15000


def instance_rmi_connection_timeout(field, value):
    return 20000


def instance_rmi_registry_ssl(field, value):
    return False


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_skip_proxy(field, value):
    return False


def instance_tags(field, value):
    return get_default_field_value(field, value)


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


def instance_tools_jar_path(field, value):
    return get_default_field_value(field, value)


def instance_trust_store_password(field, value):
    return get_default_field_value(field, value)


def instance_trust_store_path(field, value):
    return get_default_field_value(field, value)


def instance_use_legacy_auth_encoding(field, value):
    return True


def instance_user(field, value):
    return get_default_field_value(field, value)


def instance_username(field, value):
    return get_default_field_value(field, value)


def instance_web_endpoint(field, value):
    return get_default_field_value(field, value)
