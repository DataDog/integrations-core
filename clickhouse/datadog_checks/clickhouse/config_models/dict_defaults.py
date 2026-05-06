# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# The spec.yaml file does not currently support dictionary defaults, so we use this file to define them manually
# If you change a literal value here, make sure to update spec.yaml to match

from . import instance


def instance_database_identifier():
    return instance.DatabaseIdentifier(
        template="$server:$port:$db",
    )


def instance_query_samples():
    return instance.QuerySamples(
        enabled=True,
        collection_interval=1,
        payload_row_limit=1000,
        run_sync=False,
    )


def instance_query_metrics():
    return instance.QueryMetrics(
        enabled=True,
        collection_interval=10,
        run_sync=False,
        full_statement_text_cache_max_size=10000,
        full_statement_text_samples_per_hour_per_query=1,
    )


def instance_query_completions():
    return instance.QueryCompletions(
        enabled=True,
        collection_interval=10,
        samples_per_hour_per_query=15,
        seen_samples_cache_maxsize=10000,
        max_samples_per_collection=1000,
        explained_queries_per_hour_per_query=60,
        explained_queries_cache_maxsize=5000,
        run_sync=False,
    )


def instance_query_errors():
    return instance.QueryErrors(
        enabled=True,
        collection_interval=10,
        samples_per_hour_per_query=60,
        seen_samples_cache_maxsize=10000,
        max_samples_per_collection=1000,
        run_sync=False,
    )


def instance_parts_and_merges():
    return instance.PartsAndMerges(
        enabled=True,
        collection_interval=60,
        max_parts_rows=500,
        max_mutations_rows=200,
        max_detached_parts_rows=1000,
        max_replication_queue_rows=1000,
        run_sync=False,
        table_metrics_include_partition_tag=False,
        table_metrics_max_tables=200,
        stalled_merge_elapsed_threshold_seconds=3600,
        stuck_replication_num_tries=3,
    )
