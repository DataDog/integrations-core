# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_application_name(field, value):
    return 'datadog-agent'


def instance_collect_activity_metrics(field, value):
    return False


def instance_collect_count_metrics(field, value):
    return True


def instance_collect_database_size_metrics(field, value):
    return True


def instance_collect_default_database(field, value):
    return False


def instance_collect_function_metrics(field, value):
    return False


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_dbname(field, value):
    return get_default_field_value(field, value)


def instance_dbstrict(field, value):
    return False


def instance_deep_database_monitoring(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_max_relations(field, value):
    return 300


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_pg_stat_statements_view(field, value):
    return 'show_pg_stat_statements()'


def instance_port(field, value):
    return 5432


def instance_query_timeout(field, value):
    return 1000


def instance_relations(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_ssl(field, value):
    return 'false'


def instance_statement_metrics_limits(field, value):
    return get_default_field_value(field, value)


def instance_statement_samples(field, value):
    return get_default_field_value(field, value)


def instance_table_count_limit(field, value):
    return 200


def instance_tag_replication_role(field, value):
    return False


def instance_tags(field, value):
    return get_default_field_value(field, value)
