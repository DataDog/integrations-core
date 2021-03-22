{license_header}
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_conf(field, value):
    return get_default_field_value(field, value)


def shared_new_gc_metrics(field, value):
    return False


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_service_check_prefix(field, value):
    return get_default_field_value(field, value)


def instance_collect_default_jvm_metrics(field, value):
    return True


def instance_empty_default_hostname(field, value):
    return False


def instance_java_bin_path(field, value):
    return get_default_field_value(field, value)


def instance_java_options(field, value):
    return get_default_field_value(field, value)


def instance_jmx_url(field, value):
    return get_default_field_value(field, value)


def instance_key_store_password(field, value):
    return get_default_field_value(field, value)


def instance_key_store_path(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_name(field, value):
    return get_default_field_value(field, value)


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_process_name_regex(field, value):
    return get_default_field_value(field, value)


def instance_rmi_client_timeout(field, value):
    return 15000


def instance_rmi_connection_timeout(field, value):
    return 20000


def instance_rmi_registry_ssl(field, value):
    return False


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_tools_jar_path(field, value):
    return get_default_field_value(field, value)


def instance_trust_store_password(field, value):
    return get_default_field_value(field, value)


def instance_trust_store_path(field, value):
    return get_default_field_value(field, value)


def instance_user(field, value):
    return get_default_field_value(field, value)
