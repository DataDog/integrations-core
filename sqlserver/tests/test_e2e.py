# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sqlserver import SQLServer

from .common import EXPECTED_AO_METRICS_PRIMARY, EXPECTED_AO_METRICS_SECONDARY, EXPECTED_METRICS
from .utils import always_on, not_windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


pytestmark = pytest.mark.e2e


@pytest.mark.e2e
def test_check_ao_e2e_primary(dd_agent_check, init_config, instance_ao_docker_primary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': instance_ao_docker_primary})

    for mname in EXPECTED_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname)
    aggregator.assert_metric('sqlserver.ao.secondary_replica_health', count=0)


@not_windows_ci
@always_on
def test_check_ao_e2e_primary_local_only(dd_agent_check, init_config, instance_ao_docker_primary_local_only):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_local_only]})

    for mname in EXPECTED_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname, count=1)
    aggregator.assert_metric('sqlserver.ao.secondary_replica_health', count=0)


@not_windows_ci
@always_on
def test_check_ao_e2e_primary_non_exist_ag(dd_agent_check, init_config, instance_ao_docker_primary_non_existing_ag):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_non_existing_ag]})

    for mname in EXPECTED_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_check_ao_e2e_secondary(dd_agent_check, init_config, instance_ao_docker_secondary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_secondary]})

    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname)
    aggregator.assert_metric('sqlserver.ao.primary_replica_health', count=0)


def test_check_docker_e2e(dd_agent_check, init_config, instance_e2e):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_e2e]}, rate=True)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    for mname in EXPECTED_METRICS:
        aggregator.assert_metric(mname)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)

    aggregator.assert_all_metrics_covered()
