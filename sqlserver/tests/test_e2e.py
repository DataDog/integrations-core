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
    EXPECTED_METRICS,
)
from .utils import always_on, not_windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


pytestmark = pytest.mark.e2e


@not_windows_ci
@always_on
def test_check_ao_e2e_primary(dd_agent_check, init_config, instance_ao_docker_primary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname)

    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS)


@not_windows_ci
@always_on
def test_check_ao_primary_local_only(dd_agent_check, init_config, instance_ao_docker_primary_local_only):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_local_only]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=1)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_check_ao_primary_non_exist_ag(dd_agent_check, init_config, instance_ao_docker_primary_non_existing_ag):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_non_existing_ag]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=0)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_check_ao_secondary(dd_agent_check, init_config, instance_ao_docker_secondary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_secondary]})

    for mname in EXPECTED_AO_METRICS_SECONDARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname)
    for mname in EXPECTED_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS)


def test_check_docker(dd_agent_check, init_config, instance_e2e):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_e2e]}, rate=True)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    for mname in EXPECTED_METRICS:
        aggregator.assert_metric(mname)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=CUSTOM_METRICS)
