# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_countonly(field, value):
    return False


def instance_dirs_patterns_full(field, value):
    return False


def instance_dirtagname(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_exclude_dirs(field, value):
    return get_default_field_value(field, value)


def instance_filegauges(field, value):
    return False


def instance_filetagname(field, value):
    return get_default_field_value(field, value)


def instance_follow_symlinks(field, value):
    return True


def instance_ignore_missing(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_name(field, value):
    return get_default_field_value(field, value)


def instance_pattern(field, value):
    return '*'


def instance_recursive(field, value):
    return False


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_stat_follow_symlinks(field, value):
    return True


def instance_submit_histograms(field, value):
    return True


def instance_tags(field, value):
    return get_default_field_value(field, value)
