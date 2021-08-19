# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_collect_client_metrics(field, value):
    return False


def instance_command_stats(field, value):
    return False


def instance_db(field, value):
    return 0


def instance_disable_connection_cache(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_keys(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_slowlog_max_len(field, value):
    return 128


def instance_socket_timeout(field, value):
    return 5


def instance_ssl(field, value):
    return False


def instance_ssl_ca_certs(field, value):
    return get_default_field_value(field, value)


def instance_ssl_cert_reqs(field, value):
    return 2


def instance_ssl_certfile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_keyfile(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_unix_socket_path(field, value):
    return get_default_field_value(field, value)


def instance_username(field, value):
    return get_default_field_value(field, value)


def instance_warn_on_missing_keys(field, value):
    return True
