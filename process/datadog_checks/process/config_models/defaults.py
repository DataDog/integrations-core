# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_access_denied_cache_duration(field, value):
    return 120


def shared_pid_cache_duration(field, value):
    return 120


def shared_procfs_path(field, value):
    return '/proc'


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_shared_process_list_cache_duration(field, value):
    return 120


def instance_collect_children(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_exact_match(field, value):
    return True


def instance_ignore_denied_access(field, value):
    return True


def instance_min_collection_interval(field, value):
    return 15


def instance_pid(field, value):
    return get_default_field_value(field, value)


def instance_pid_file(field, value):
    return get_default_field_value(field, value)


def instance_search_string(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_thresholds(field, value):
    return get_default_field_value(field, value)


def instance_try_sudo(field, value):
    return False


def instance_user(field, value):
    return get_default_field_value(field, value)
