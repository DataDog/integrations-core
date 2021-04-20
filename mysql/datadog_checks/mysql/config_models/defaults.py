# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_global_custom_queries(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_charset(field, value):
    return 'utf8'


def instance_connect_timeout(field, value):
    return 10


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_deep_database_monitoring(field, value):
    return False


def instance_defaults_file(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_host(field, value):
    return 'localhost'


def instance_max_custom_queries(field, value):
    return 20


def instance_min_collection_interval(field, value):
    return 15


def instance_options(field, value):
    return get_default_field_value(field, value)


def instance_pass_(field, value):
    return get_default_field_value(field, value)


def instance_port(field, value):
    return 3306


def instance_queries(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_sock(field, value):
    return get_default_field_value(field, value)


def instance_ssl(field, value):
    return get_default_field_value(field, value)


def instance_statement_metrics_limits(field, value):
    return get_default_field_value(field, value)


def instance_statement_samples(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_use_global_custom_queries(field, value):
    return 'true'


def instance_user(field, value):
    return 'datadog'
