# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_deprecated(field, value):
    return get_default_field_value(field, value)


def shared_timeout(field, value):
    return get_default_field_value(field, value)


def instance_array(field, value):
    return get_default_field_value(field, value)


def instance_deprecated(field, value):
    return get_default_field_value(field, value)


def instance_flag(field, value):
    return False


def instance_hyphenated_name(field, value):
    return get_default_field_value(field, value)


def instance_mapping(field, value):
    return get_default_field_value(field, value)


def instance_obj(field, value):
    return get_default_field_value(field, value)


def instance_pass_(field, value):
    return get_default_field_value(field, value)


def instance_pid(field, value):
    return get_default_field_value(field, value)


def instance_text(field, value):
    return get_default_field_value(field, value)


def instance_timeout(field, value):
    return get_default_field_value(field, value)
