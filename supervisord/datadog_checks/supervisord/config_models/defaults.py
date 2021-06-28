# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_host(field, value):
    return 'localhost'


def instance_min_collection_interval(field, value):
    return 15


def instance_pass_(field, value):
    return get_default_field_value(field, value)


def instance_port(field, value):
    return 9001


def instance_proc_names(field, value):
    return get_default_field_value(field, value)


def instance_proc_regex(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_socket(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_user(field, value):
    return get_default_field_value(field, value)
