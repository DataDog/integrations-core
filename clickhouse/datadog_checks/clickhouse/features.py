# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
ClickHouse feature definitions for configuration health reporting.

This module defines the features that can be enabled/disabled in ClickHouse DBM,
following the same pattern as Postgres for consistency.
"""

from enum import Enum
from typing import TypedDict


class FeatureKey(Enum):
    """
    Enum representing the keys for features in the ClickHouse configuration.
    """

    DBM = "dbm"
    QUERY_METRICS = "query_metrics"
    QUERY_SAMPLES = "query_samples"
    COMPLETED_QUERY_SAMPLES = "completed_query_samples"
    SINGLE_ENDPOINT_MODE = "single_endpoint_mode"


FeatureNames = {
    FeatureKey.DBM: 'Database Monitoring',
    FeatureKey.QUERY_METRICS: 'Query Metrics',
    FeatureKey.QUERY_SAMPLES: 'Query Samples',
    FeatureKey.COMPLETED_QUERY_SAMPLES: 'Completed Query Samples',
    FeatureKey.SINGLE_ENDPOINT_MODE: 'Single Endpoint Mode',
}


class Feature(TypedDict):
    """
    A feature in the ClickHouse configuration that can be enabled or disabled.
    """

    key: str
    name: str
    enabled: bool
    description: str | None
