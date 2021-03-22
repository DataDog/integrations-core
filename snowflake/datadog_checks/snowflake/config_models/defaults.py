# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_global_custom_queries(field, value):
    return get_default_field_value(field, value)


def shared_proxy_host(field, value):
    return get_default_field_value(field, value)


def shared_proxy_password(field, value):
    return get_default_field_value(field, value)


def shared_proxy_port(field, value):
    return get_default_field_value(field, value)


def shared_proxy_user(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_authenticator(field, value):
    return get_default_field_value(field, value)


def instance_client_prefetch_threads(field, value):
    return 4


def instance_client_session_keep_alive(field, value):
    return False


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_database(field, value):
    return 'SNOWFLAKE'


def instance_empty_default_hostname(field, value):
    return False


def instance_login_timeout(field, value):
    return 60


def instance_metric_groups(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 3600


def instance_ocsp_response_cache_filename(field, value):
    return get_default_field_value(field, value)


def instance_schema(field, value):
    return 'ACCOUNT_USAGE'


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_token(field, value):
    return get_default_field_value(field, value)


def instance_use_global_custom_queries(field, value):
    return 'true'


def instance_warehouse(field, value):
    return get_default_field_value(field, value)
