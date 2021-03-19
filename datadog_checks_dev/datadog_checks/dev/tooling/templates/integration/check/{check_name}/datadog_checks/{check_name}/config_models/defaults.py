{license_header}
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)
