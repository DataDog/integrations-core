# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.config import PostgresConfig
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache
from datadog_checks.postgres.util import REPLICATION_METRICS_9_1, REPLICATION_METRICS_10
from datadog_checks.postgres.version_utils import V9_1, V9_2, V10


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, is_aurora, expected_metrics',
    [
        pytest.param(V10, False, REPLICATION_METRICS_10),
        pytest.param(V10, True, {}),
        pytest.param(V9_1, False, REPLICATION_METRICS_9_1),
        pytest.param(V9_2, True, {}),
    ],
)
def test_aurora_replication_metrics(pg_instance, version, is_aurora, expected_metrics):
    config = PostgresConfig(pg_instance)
    cache = PostgresMetricsCache(config)
    replication_metrics = cache.get_replication_metrics(version, is_aurora)
    assert replication_metrics == expected_metrics
