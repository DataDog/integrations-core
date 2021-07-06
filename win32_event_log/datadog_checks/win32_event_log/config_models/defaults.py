# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_default_event_priority(field, value):
    return 'normal'


def shared_event_priority(field, value):
    return 'normal'


def shared_interpret_messages(field, value):
    return True


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_tag_event_id(field, value):
    return False


def shared_tag_sid(field, value):
    return False


def instance_auth_type(field, value):
    return 'default'


def instance_bookmark_frequency(field, value):
    return get_default_field_value(field, value)


def instance_domain(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_event_format(field, value):
    return get_default_field_value(field, value)


def instance_event_id(field, value):
    return get_default_field_value(field, value)


def instance_event_priority(field, value):
    return 'normal'


def instance_excluded_messages(field, value):
    return get_default_field_value(field, value)


def instance_filters(field, value):
    return get_default_field_value(field, value)


def instance_host(field, value):
    return get_default_field_value(field, value)


def instance_included_messages(field, value):
    return get_default_field_value(field, value)


def instance_interpret_messages(field, value):
    return True


def instance_legacy_mode(field, value):
    return False


def instance_log_file(field, value):
    return get_default_field_value(field, value)


def instance_message_filters(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_path(field, value):
    return get_default_field_value(field, value)


def instance_payload_size(field, value):
    return 10


def instance_query(field, value):
    return get_default_field_value(field, value)


def instance_server(field, value):
    return 'localhost'


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_source_name(field, value):
    return get_default_field_value(field, value)


def instance_start(field, value):
    return 'now'


def instance_tag_event_id(field, value):
    return False


def instance_tag_sid(field, value):
    return False


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_timeout(field, value):
    return 5


def instance_type(field, value):
    return get_default_field_value(field, value)


def instance_user(field, value):
    return get_default_field_value(field, value)
