# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from copy import deepcopy

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.conftest import load_fixture_page
from tests.constants import OFF_VM_NAME, OFF_VM_TAGS, PCVM_NAME, PCVM_TAGS, UBUNTU_VM_NAME, UBUNTU_VM_TAGS
from tests.metrics import VM_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.unit]


def test_vm_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=PCVM_TAGS)


def test_vm_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=PCVM_TAGS)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_off_vms_skipped_by_default(dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection):
    """VMs with powerState OFF are skipped by default regardless of collection mode."""
    mock_instance["batch_vm_collection"] = batch_vm_collection
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) == 4
    vm_names = {tag.split(":")[1] for m in vm_metrics for tag in m.tags if tag.startswith("ntnx_vm_name:")}
    assert "test-vm-that-should-remain-off" not in vm_names


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_off_vms_collected_with_wildcard_filter(
    dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection
):
    """A wildcard powerState filter ('.*') overrides the ON-only default and collects OFF VMs.

    Covers both OFF VMs in the fixtures: ``test-vm-that-should-remain-off`` (attached to a host)
    and ``hostless-vm-second-cluster`` (no host, as powered-off AHV VMs report no host field).
    All 6 VMs (4 ON + 2 OFF) are collected.
    """
    mock_instance["batch_vm_collection"] = batch_vm_collection
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "powerState", "patterns": [".*"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    vm_names = {tag.split(":", 1)[1] for m in vm_metrics for tag in m.tags if tag.startswith("ntnx_vm_name:")}
    assert len(vm_metrics) == 6
    assert "test-vm-that-should-remain-off" in vm_names
    assert "hostless-vm-second-cluster" in vm_names


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_hostless_off_vm_collected_with_filter(
    dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection
):
    """A powered-off VM with no host assignment is collected when a powerState filter allows OFF."""
    mock_instance["batch_vm_collection"] = batch_vm_collection
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "powerState", "patterns": ["^(ON|OFF)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    hostless = next(
        m for m in aggregator.metrics("nutanix.vm.count") if "ntnx_vm_name:hostless-vm-second-cluster" in m.tags
    )
    assert "ntnx_power_state:off" in hostless.tags
    assert "ntnx_cluster_name:second-nutanix-cluster" in hostless.tags
    assert not any(tag.startswith("ntnx_host_name:") for tag in hostless.tags)


def test_off_vm_skip_logged_at_debug(dd_run_check, aggregator, mock_instance, mock_http_get, caplog):
    """The default ON-only skip logs the skipped VM and the reason at debug level."""
    with caplog.at_level(logging.DEBUG):
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

    assert any(
        "Skipping VM" in r.message and "powerState=OFF" in r.message and "no powerState resource filter" in r.message
        for r in caplog.records
    )


def test_vm_status_off(dd_run_check, aggregator, mock_instance, mock_http_get):
    """VM fixture has powerState=OFF which maps to status value 2."""
    mock_instance["batch_vm_collection"] = False
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "powerState", "patterns": ["^(ON|OFF)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.status", value=2, tags=OFF_VM_TAGS, hostname=OFF_VM_NAME)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_batch_and_non_batch_produce_same_counts(
    dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection
):
    mock_instance["batch_vm_collection"] = batch_vm_collection
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    assert check.infrastructure_monitor.cluster_count == 2
    assert check.infrastructure_monitor.host_count == 2
    assert check.infrastructure_monitor.vm_count == 4
    aggregator.assert_metric("nutanix.vm.count", count=4)
    aggregator.assert_metric("nutanix.host.count", count=2)
    aggregator.assert_metric("nutanix.cluster.count", count=2)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_vms_collected_when_host_missing_name(
    dd_run_check, aggregator, mock_instance, mock_http_get, mocker, batch_vm_collection
) -> None:
    mock_instance["batch_vm_collection"] = batch_vm_collection

    hosts = deepcopy(load_fixture_page("hosts_00064715.json", 0)["data"])
    hosts[0].pop("hostName")
    hosts_by_cluster = {
        "00064715-c043-5d8f-ee4b-176ec875554d": hosts,
        "aabbccdd-1111-2222-3333-444455556666": deepcopy(load_fixture_page("hosts_aabbccdd.json", 0)["data"]),
    }
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_hosts_by_cluster",
        side_effect=lambda cluster_id: hosts_by_cluster[cluster_id],
    )

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    vm_names = {
        tag.split(":", 1)[1]
        for m in aggregator.metrics("nutanix.vm.count")
        for tag in m.tags
        if tag.startswith("ntnx_vm_name:")
    }
    assert {PCVM_NAME, "ubuntu-vm", "random-vm"}.issubset(vm_names)
    assert check.infrastructure_monitor.host_count == 1
    aggregator.assert_metric("nutanix.vm.count", count=4)
    aggregator.assert_metric("nutanix.host.count", count=1)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_vm_with_no_extid_is_skipped(
    dd_run_check, aggregator, mock_instance, mock_http_get, mocker, batch_vm_collection
) -> None:
    mock_instance["batch_vm_collection"] = batch_vm_collection

    all_vms = deepcopy(load_fixture_page("vms.json", 0)["data"])
    vms_by_host: dict[str, list] = {}
    for vm in all_vms:
        host_id = (vm.get("host") or {}).get("extId") or ""
        vms_by_host.setdefault(host_id, []).append(vm)

    ubuntu_vm = next(v for v in vms_by_host["d8787814-4fe8-4ba5-931f-e1ee31c294a6"] if v.get("name") == "ubuntu-vm")
    ubuntu_vm.pop("extId")

    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._get_vms_for_host",
        side_effect=lambda h: vms_by_host.get(h, []),
    )

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    assert check.infrastructure_monitor.vm_count == 3
    vm_names = {
        tag.split(":", 1)[1]
        for m in aggregator.metrics("nutanix.vm.count")
        for tag in m.tags
        if tag.startswith("ntnx_vm_name:")
    }
    assert "ubuntu-vm" not in vm_names


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_vm_with_no_name_is_skipped(
    dd_run_check, aggregator, mock_instance, mock_http_get, mocker, batch_vm_collection
) -> None:
    mock_instance["batch_vm_collection"] = batch_vm_collection

    all_vms = deepcopy(load_fixture_page("vms.json", 0)["data"])
    vms_by_host: dict[str, list] = {}
    for vm in all_vms:
        host_id = (vm.get("host") or {}).get("extId") or ""
        vms_by_host.setdefault(host_id, []).append(vm)

    ubuntu_vm = next(v for v in vms_by_host["d8787814-4fe8-4ba5-931f-e1ee31c294a6"] if v.get("name") == "ubuntu-vm")
    ubuntu_vm.pop("name")

    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._get_vms_for_host",
        side_effect=lambda h: vms_by_host.get(h, []),
    )

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    assert check.infrastructure_monitor.vm_count == 3
    aggregator.assert_metric("nutanix.vm.count", count=3)


def test_external_tags_for_vm(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(
        PCVM_NAME,
        {'nutanix': PCVM_TAGS},
    )


def test_hostname_transform_upper_applies_to_vm(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['hostname_transform'] = 'upper'
    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=UBUNTU_VM_TAGS, hostname=UBUNTU_VM_NAME.upper())


def test_hostname_transform_lower_applies_to_vm(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['hostname_transform'] = 'lower'
    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=PCVM_TAGS, hostname=PCVM_NAME.lower())
