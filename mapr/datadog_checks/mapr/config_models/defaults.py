# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_hostname(field, value):
    return get_default_field_value(field, value)


def instance_metric_whitelist(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_stream_path(field, value):
    return '/var/mapr/mapr.monitoring/metricstreams'


def instance_streams_count(field, value):
    return 1


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_ticket_location(field, value):
    return get_default_field_value(field, value)
