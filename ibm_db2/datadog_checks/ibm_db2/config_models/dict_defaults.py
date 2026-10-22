# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# The spec.yaml file does not currently support dictionary defaults, so we use this file to define them manually
# If you change a literal value here, make sure to update spec.yaml to match

from . import instance


def instance_collect_schemas():
    return instance.CollectSchemas(
        enabled=True,
        collection_interval=600,
        max_tables=300,
        max_columns=50,
        max_query_duration=60,
        include_schemas=[],
        exclude_schemas=[],
        include_tables=[],
        exclude_tables=[],
    )
