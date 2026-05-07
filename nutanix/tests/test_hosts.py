# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME, HOST_TAGS
from tests.metrics import HOST_STATS_METRICS_REQUIRED, HOST_STORAGE_METRICS

pytestmark = [pytest.mark.unit]


def test_host_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.count", value=1, tags=HOST_TAGS, hostname=HOST_NAME)


def test_host_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in HOST_STATS_METRICS_REQUIRED:
        expected_tags = HOST_TAGS + ['ntnx_disk_status:normal'] if metric in HOST_STORAGE_METRICS else HOST_TAGS
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags, hostname=HOST_NAME)


def test_host_storage_metrics_have_disk_status_tag(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Storage metrics carry ntnx_disk_status; non-storage host metrics do not."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.host.storage_capacity", at_least=1, tags=HOST_TAGS + ['ntnx_disk_status:normal'], hostname=HOST_NAME
    )
    for metric_obj in aggregator.metrics("nutanix.host.cpu_capacity"):
        assert not any(t.startswith("ntnx_disk_status:") for t in metric_obj.tags)


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
