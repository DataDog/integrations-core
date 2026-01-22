# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# The spec.yaml file does not currently support dictionary defaults, so we use this file to define them manually
# If you change a literal value here, make sure to update spec.yaml to match

from . import instance


def instance_query_activity():
    return instance.QueryActivity(
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


def instance_completed_query_samples():
    return instance.CompletedQuerySamples(
        enabled=True,
        collection_interval=10,
        samples_per_hour_per_query=15,
        seen_samples_cache_maxsize=10000,
        max_samples_per_collection=1000,
        run_sync=False,
    )
