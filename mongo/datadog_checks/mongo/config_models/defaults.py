# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_additional_metrics(field, value):
    return get_default_field_value(field, value)


def instance_collections(field, value):
    return get_default_field_value(field, value)


def instance_collections_indexes_stats(field, value):
    return False


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_database(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_hosts(field, value):
    return get_default_field_value(field, value)


def instance_min_collection_interval(field, value):
    return 15


def instance_options(field, value):
    return get_default_field_value(field, value)


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_replica_check(field, value):
    return True


def instance_server(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_ssl(field, value):
    return False


def instance_ssl_ca_certs(field, value):
    return get_default_field_value(field, value)


def instance_ssl_cert_reqs(field, value):
    return get_default_field_value(field, value)


def instance_ssl_certfile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_keyfile(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_timeout(field, value):
    return 30


def instance_username(field, value):
    return get_default_field_value(field, value)
