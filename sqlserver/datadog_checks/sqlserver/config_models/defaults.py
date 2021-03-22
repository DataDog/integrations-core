# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_custom_metrics(field, value):
    return get_default_field_value(field, value)


def shared_global_custom_queries(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_adoprovider(field, value):
    return 'SQLOLEDB'


def instance_ao_database(field, value):
    return get_default_field_value(field, value)


def instance_autodiscovery_exclude(field, value):
    return get_default_field_value(field, value)


def instance_autodiscovery_include(field, value):
    return get_default_field_value(field, value)


def instance_availability_group(field, value):
    return get_default_field_value(field, value)


def instance_command_timeout(field, value):
    return 5


def instance_connection_string(field, value):
    return get_default_field_value(field, value)


def instance_connector(field, value):
    return 'adodbapi'


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_database(field, value):
    return 'master'


def instance_database_autodiscovery(field, value):
    return False


def instance_database_autodiscovery_interval(field, value):
    return 3600


def instance_db_fragmentation_object_names(field, value):
    return get_default_field_value(field, value)


def instance_driver(field, value):
    return 'SQL Server'


def instance_dsn(field, value):
    return get_default_field_value(field, value)


def instance_empty_default_hostname(field, value):
    return False


def instance_ignore_missing_database(field, value):
    return False


def instance_include_ao_metrics(field, value):
    return False


def instance_include_db_fragmentation_metrics(field, value):
    return False


def instance_include_fci_metrics(field, value):
    return False


def instance_include_instance_metrics(field, value):
    return True


def instance_include_task_scheduler_metrics(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_only_emit_local(field, value):
    return False


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_proc_only_if(field, value):
    return get_default_field_value(field, value)


def instance_proc_only_if_database(field, value):
    return 'master'


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_stored_procedure(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_use_global_custom_queries(field, value):
    return 'true'


def instance_username(field, value):
    return get_default_field_value(field, value)
