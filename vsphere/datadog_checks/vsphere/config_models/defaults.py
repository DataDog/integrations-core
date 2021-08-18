# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_rest_api_options(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_attributes_prefix(field, value):
    return ''


def instance_batch_property_collector_size(field, value):
    return 500


def instance_batch_tags_collector_size(field, value):
    return 200


def instance_collect_attributes(field, value):
    return False


def instance_collect_events(field, value):
    return get_default_field_value(field, value)


def instance_collect_events_only(field, value):
    return False


def instance_collect_per_instance_filters(field, value):
    return get_default_field_value(field, value)


def instance_collect_tags(field, value):
    return False


def instance_collection_level(field, value):
    return 1


def instance_collection_type(field, value):
    return 'realtime'


def instance_excluded_host_tags(field, value):
    return []


def instance_include_datastore_cluster_folder_tag(field, value):
    return True


def instance_max_historical_metrics(field, value):
    return 256


def instance_metric_filters(field, value):
    return get_default_field_value(field, value)


def instance_metrics_per_query(field, value):
    return 500


def instance_min_collection_interval(field, value):
    return 15


def instance_refresh_infrastructure_cache_interval(field, value):
    return 300


def instance_refresh_metrics_metadata_cache_interval(field, value):
    return 1800


def instance_resource_filters(field, value):
    return get_default_field_value(field, value)


def instance_rest_api_options(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_ssl_capath(field, value):
    return get_default_field_value(field, value)


def instance_ssl_verify(field, value):
    return True


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_tags_prefix(field, value):
    return ''


def instance_threads_count(field, value):
    return 4


def instance_tls_ignore_warning(field, value):
    return False


def instance_use_collect_events_fallback(field, value):
    return False


def instance_use_guest_hostname(field, value):
    return False
