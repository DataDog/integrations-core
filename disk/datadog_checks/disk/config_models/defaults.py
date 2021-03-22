# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_device_global_exclude(field, value):
    return get_default_field_value(field, value)


def shared_file_system_global_exclude(field, value):
    return get_default_field_value(field, value)


def shared_mount_point_global_exclude(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_all_partitions(field, value):
    return False


def instance_blkid_cache_file(field, value):
    return '/run/blkid/blkid.tab'


def instance_create_mounts(field, value):
    return get_default_field_value(field, value)


def instance_device_exclude(field, value):
    return get_default_field_value(field, value)


def instance_device_include(field, value):
    return get_default_field_value(field, value)


def instance_device_tag_re(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_file_system_exclude(field, value):
    return get_default_field_value(field, value)


def instance_file_system_include(field, value):
    return get_default_field_value(field, value)


def instance_include_all_devices(field, value):
    return True


def instance_min_collection_interval(field, value):
    return 15


def instance_min_disk_size(field, value):
    return 0


def instance_mount_point_exclude(field, value):
    return get_default_field_value(field, value)


def instance_mount_point_include(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_service_check_rw(field, value):
    return False


def instance_tag_by_filesystem(field, value):
    return False


def instance_tag_by_label(field, value):
    return True


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_timeout(field, value):
    return 5
