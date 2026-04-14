# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import BASE_TAGS, CLUSTER_TAGS

pytestmark = [pytest.mark.unit]


def test_health_check_success(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=BASE_TAGS)


def test_health_check_failure(dd_run_check, aggregator, mock_instance, mocker):
    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError

        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1, tags=BASE_TAGS)


def test_cluster_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.nbr_nodes", value=1, tags=CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.vm.count", value=5, tags=CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.vm.inefficient_count", value=0, tags=CLUSTER_TAGS)


def test_cluster_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    from tests.metrics import CLUSTER_STATS_METRICS_REQUIRED

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=CLUSTER_TAGS)


def test_entity_counts(dd_run_check, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    infra = check.infrastructure_monitor
    activity = check.activity_monitor

    assert infra.cluster_count == 2
    assert infra.host_count == 2
    assert infra.vm_count == 4
    assert activity.events_count == 0
    assert activity.tasks_count == 0
    assert activity.audits_count == 0
    assert activity.alerts_count == 0


def test_summary_log_message(dd_run_check, mock_instance, mock_http_get, caplog):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    with caplog.at_level(logging.INFO):
        dd_run_check(check)

    expected = "[PC:10.0.0.197] Check completed: 2 clusters, 2 hosts, 4 VMs, 0 events, 0 tasks, 0 audits, 0 alerts"
    summary_lines = [r.message for r in caplog.records if "Check completed" in r.message]
    assert len(summary_lines) == 1
    assert summary_lines[0] == expected


def test_prism_central_cluster_skipped(dd_run_check, aggregator, mock_instance, mock_http_get, caplog):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    with caplog.at_level(logging.INFO):
        dd_run_check(check)

    assert any("Skipping Prism Central cluster: prism-central-deployment" in r.message for r in caplog.records)
    pc_metrics = [
        m for m in aggregator.metrics("nutanix.cluster.count") if any("prism-central-deployment" in t for t in m.tags)
    ]
    assert len(pc_metrics) == 0


def test_missing_pc_ip_raises_error(dd_run_check):
    with pytest.raises(Exception, match="(?s)pc_ip.*required"):
        check = NutanixCheck('nutanix', {}, [{"pc_username": "admin", "pc_password": "secret"}])
        dd_run_check(check)


def test_pc_ip_with_port_raises_error(dd_run_check, mock_instance):
    """Test that ConfigurationError is raised when pc_ip contains a port."""

    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197:9440'

    with pytest.raises(Exception, match="Conflicting port configuration"):
        check = NutanixCheck('nutanix', {}, [instance])
        dd_run_check(check)


def test_pc_ip_without_port(dd_run_check, mock_instance, mock_http_get):
    """Test that pc_port is used when pc_ip has no port."""
    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197'

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    assert check.pc_ip == '10.0.0.197'
    assert check.pc_port == 9440
    assert check.base_url == 'https://10.0.0.197:9440'
