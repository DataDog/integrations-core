# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.sqlserver import SQLServer

from .common import (
    CUSTOM_METRICS,
    EXPECTED_AO_METRICS_COMMON,
    EXPECTED_AO_METRICS_PRIMARY,
    EXPECTED_AO_METRICS_SECONDARY,
    EXPECTED_METRICS_DBM_ENABLED,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY,
    UNDOCUMENTED_METRICS,
    UNEXPECTED_FCI_METRICS,
    UNEXPECTED_QUERY_EXECUTOR_AO_METRICS,
)
from .utils import always_on, not_windows_ado, not_windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None

pytestmark = pytest.mark.e2e


@not_windows_ci
@always_on
def test_ao_primary_replica(dd_agent_check, init_config, instance_ao_docker_primary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary]})

    # Metrics that are expected to be collected from the primary replica, this includes
    # metrics for secondary replicas.
    for mname in (
        EXPECTED_AO_METRICS_PRIMARY
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY
        + EXPECTED_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY
    ):
        aggregator.assert_metric(mname)

    # Metrics that can only be collected from the secondary replica, regardless
    # of being connected to the primary replica.
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS + UNDOCUMENTED_METRICS)


@not_windows_ci
@always_on
def test_ao_local_primary_replica_only(dd_agent_check, init_config, instance_ao_docker_primary_local_only):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_local_only]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=1)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_ao_primary_with_non_exist_ag(dd_agent_check, init_config, instance_ao_docker_primary_non_existing_ag):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_non_existing_ag]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=0)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_ao_secondary_replica(dd_agent_check, init_config, instance_ao_docker_secondary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_secondary]})

    for mname in (
        EXPECTED_AO_METRICS_SECONDARY
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY
        + EXPECTED_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON
    ):
        aggregator.assert_metric(mname)
    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS + UNDOCUMENTED_METRICS)


@not_windows_ado
def test_check_docker(dd_agent_check, init_config, instance_e2e):
    # run run sync to ensure only a single run of both
    instance_e2e['query_activity'] = {'run_sync': True}
    instance_e2e['query_metrics'] = {'run_sync': True}
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_e2e]}, rate=True)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    # ignore DBM debug metrics for the following tests as they're not currently part of the public set of product
    # metrics
    dbm_debug_metrics = [m for m in aggregator._metrics.keys() if m.startswith('dd.sqlserver.')]
    for m in dbm_debug_metrics:
        del aggregator._metrics[m]

    for mname in EXPECTED_METRICS_DBM_ENABLED:
        aggregator.assert_metric(mname)

    for mname in UNEXPECTED_FCI_METRICS + UNEXPECTED_QUERY_EXECUTOR_AO_METRICS:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS + UNDOCUMENTED_METRICS)
