# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_global_custom_queries(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_compression(field, value):
    return get_default_field_value(field, value)


def instance_connect_timeout(field, value):
    return 10


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_db(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_port(field, value):
    return 9000


def instance_read_timeout(field, value):
    return 10


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_tls_verify(field, value):
    return False


def instance_use_global_custom_queries(field, value):
    return 'true'


def instance_user(field, value):
    return 'default'
