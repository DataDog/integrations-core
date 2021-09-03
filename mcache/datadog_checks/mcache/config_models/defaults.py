# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_options(field, value):
    return get_default_field_value(field, value)


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_port(field, value):
    return 11211


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_socket(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_url(field, value):
    return 'localhost'


def instance_username(field, value):
    return get_default_field_value(field, value)
