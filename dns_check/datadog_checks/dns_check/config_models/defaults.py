# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_default_timeout(field, value):
    return 5


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_nameserver(field, value):
    return get_default_field_value(field, value)


def instance_nameserver_port(field, value):
    return 53


def instance_record_type(field, value):
    return 'A'


def instance_resolves_as(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_timeout(field, value):
    return 5
