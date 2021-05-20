# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_kafka_timeout(field, value):
    return 5


def shared_service(field, value):
    return get_default_field_value(field, value)


def shared_zk_timeout(field, value):
    return 5


def instance_broker_requests_batch_size(field, value):
    return 30


def instance_consumer_groups(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_kafka_client_api_version(field, value):
    return '2.3.0'


def instance_kafka_consumer_offsets(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_monitor_all_broker_highwatermarks(field, value):
    return False


def instance_monitor_unlisted_consumer_groups(field, value):
    return False


def instance_sasl_kerberos_domain_name(field, value):
    return 'localhost'


def instance_sasl_kerberos_service_name(field, value):
    return 'kafka'


def instance_sasl_mechanism(field, value):
    return 'PLAIN'


def instance_sasl_plain_password(field, value):
    return get_default_field_value(field, value)


def instance_sasl_plain_username(field, value):
    return get_default_field_value(field, value)


def instance_security_protocol(field, value):
    return 'PLAINTEXT'


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_ssl_cafile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_certfile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_check_hostname(field, value):
    return True


def instance_ssl_context(field, value):
    return get_default_field_value(field, value)


def instance_ssl_crlfile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_keyfile(field, value):
    return get_default_field_value(field, value)


def instance_ssl_password(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_zk_connect_str(field, value):
    return get_default_field_value(field, value)


def instance_zk_prefix(field, value):
    return get_default_field_value(field, value)
