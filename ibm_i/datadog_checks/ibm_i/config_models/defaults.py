# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_connection_string(field, value):
    return get_default_field_value(field, value)


def instance_disable_generic_tags(field, value):
    return False


def instance_driver(field, value):
    return 'iSeries Access ODBC Driver'


def instance_empty_default_hostname(field, value):
    return False


def instance_job_query_timeout(field, value):
    return 240


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_query_timeout(field, value):
    return 30


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_severity_threshold(field, value):
    return 50


def instance_system(field, value):
    return get_default_field_value(field, value)


def instance_system_mq_query_timeout(field, value):
    return 80


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_username(field, value):
    return get_default_field_value(field, value)
