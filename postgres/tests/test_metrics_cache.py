# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.config import PostgresConfig
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache
from datadog_checks.postgres.util import (
    COMMON_METRICS,
    DBM_MIGRATED_METRICS,
    NEWER_92_METRICS,
    REPLICATION_METRICS_9_1,
    REPLICATION_METRICS_10,
)
from datadog_checks.postgres.version_utils import V9_1, V9_2, V10

COMMON_AND_MAIN_CHECK_METRICS = dict(COMMON_METRICS, **DBM_MIGRATED_METRICS)


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
    config = PostgresConfig(instance=pg_instance, init_config={})
    cache = PostgresMetricsCache(config)
    replication_metrics = cache.get_replication_metrics(version, is_aurora)
    assert replication_metrics == expected_metrics


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, is_dbm_enabled, expected_metrics',
    [
        pytest.param(V10, True, dict(COMMON_METRICS, **NEWER_92_METRICS)),
        pytest.param(V10, False, dict(COMMON_AND_MAIN_CHECK_METRICS, **NEWER_92_METRICS)),
        pytest.param(V9_1, True, COMMON_METRICS),
        pytest.param(V9_1, False, COMMON_AND_MAIN_CHECK_METRICS),
        pytest.param(V9_2, True, dict(COMMON_METRICS, **NEWER_92_METRICS)),
        pytest.param(V9_2, False, dict(COMMON_AND_MAIN_CHECK_METRICS, **NEWER_92_METRICS)),
    ],
)
def test_dbm_enabled_conn_metric(pg_instance, version, is_dbm_enabled, expected_metrics):
    pg_instance['dbm'] = is_dbm_enabled
    pg_instance['collect_resources'] = {'enabled': False}
    pg_instance['collect_database_size_metrics'] = False
    config = PostgresConfig(instance=pg_instance, init_config={})
    cache = PostgresMetricsCache(config)
    instance_metrics = cache.get_instance_metrics(version)
    assert instance_metrics['metrics'] == expected_metrics
