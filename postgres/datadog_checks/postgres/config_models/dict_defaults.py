# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# The spec.yaml file does not currently support dictionary defaults, so we use this file to define them manually
# If you change a literal value here, make sure to update spec.yaml to match

from . import instance


def instance_database_identifier():
    return instance.DatabaseIdentifier(
        template="$resolved_hostname",
    )


def instance_database_autodiscovery():
    return instance.DatabaseAutodiscovery(
        enabled=False,
        global_view_db="postgres",
        max_databases=100,
        include=[".*"],
        exclude=["cloudsqladmin", "rdsadmin", "alloydbadmin", "alloydbmetadata"],
        refresh=600,
    )


def instance_query_metrics():
    return instance.QueryMetrics(
        enabled=True,
        collection_interval=10,
        pg_stat_statements_max_warning_threshold=10000,
        incremental_query_metrics=False,
        baseline_metrics_expiry=300,
        full_statement_text_cache_max_size=10000,
        full_statement_text_samples_per_hour_per_query=10000,
        run_sync=False,
    )


def instance_query_samples():
    return instance.QuerySamples(
        enabled=True,
        collection_interval=1,
        explain_function="datadog.explain_statement",
        explained_queries_per_hour_per_query=60,
        samples_per_hour_per_query=15,
        explained_queries_cache_maxsize=5000,
        seen_samples_cache_maxsize=10000,
        explain_parameterized_queries=True,
        explain_errors_cache_maxsize=5000,
        explain_errors_cache_ttl=86400,
        run_sync=False,
    )


def instance_query_activity():
    return instance.QueryActivity(
        enabled=True,
        collection_interval=10,
        payload_row_limit=3500,
    )


def instance_collect_settings():
    return instance.CollectSettings(
        enabled=True,
        collection_interval=600,
        ignored_settings_patterns=["plpgsql%"],
        run_sync=False,
    )


def instance_collect_schemas():
    return instance.CollectSchemas(
        enabled=False,
        max_tables=300,
        max_columns=50,
        collection_interval=600,
        include_databases=[],
        exclude_databases=[],
        include_schemas=[],
        exclude_schemas=[],
        include_tables=[],
        exclude_tables=[],
        max_query_duration=60,
    )


def instance_obfuscator_options():
    return instance.ObfuscatorOptions(
        obfuscation_mode="obfuscate_and_normalize",
        replace_digits=False,
        collect_metadata=True,
        collect_tables=True,
        collect_commands=True,
        collect_comments=True,
        keep_sql_alias=True,
        keep_dollar_quoted_func=True,
        remove_space_between_parentheses=False,
        keep_null=False,
        keep_boolean=False,
        keep_positional_parameter=False,
        keep_trailing_semicolon=False,
        keep_identifier_quotation=False,
        keep_json_path=False,
    )


def instance_collect_raw_query_statement():
    return instance.CollectRawQueryStatement(
        enabled=False,
    )


def instance_locks_idle_in_transaction():
    return instance.LocksIdleInTransaction(
        enabled=True,
        collection_interval=300,
        max_rows=100,
    )
