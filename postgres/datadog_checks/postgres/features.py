# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from enum import Enum
from typing import TypedDict


class FeatureKey(Enum):
    """
    Enum representing the keys for features in the Postgres configuration.
    """

    RELATION_METRICS = "relation_metrics"
    QUERY_SAMPLES = "query_samples"
    COLLECT_SETTINGS = "collect_settings"
    COLLECT_SCHEMAS = "collect_schemas"
    QUERY_ACTIVITY = "query_activity"
    QUERY_METRICS = "query_metrics"


FeatureNames = {
    FeatureKey.RELATION_METRICS: 'Relation Metrics',
    FeatureKey.QUERY_SAMPLES: 'Query Samples',
    FeatureKey.COLLECT_SETTINGS: 'Collect Settings',
    FeatureKey.COLLECT_SCHEMAS: 'Collect Schemas',
    FeatureKey.QUERY_ACTIVITY: 'Query Activity',
    FeatureKey.QUERY_METRICS: 'Query Metrics',
}


class Feature(TypedDict):
    """
    A feature in the Postgres configuration that can be enabled or disabled.
    """

    key: str
    name: str
    enabled: bool
    description: str | None
