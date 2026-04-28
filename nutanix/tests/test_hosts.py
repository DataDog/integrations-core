# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME, HOST_TAGS
from tests.metrics import HOST_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.unit]


def test_host_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.count", value=1, tags=HOST_TAGS, hostname=HOST_NAME)


def test_host_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in HOST_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=HOST_TAGS, hostname=HOST_NAME)


def test_host_status_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Host fixture has nodeStatus=NORMAL which maps to status value 0 (OK)."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.host.status", value=0, tags=HOST_TAGS + ['ntnx_node_status:NORMAL'], hostname=HOST_NAME
    )


def test_external_tags_for_host(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(
        HOST_NAME,
        {'nutanix': HOST_TAGS},
    )
