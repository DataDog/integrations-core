# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""End-to-end coverage that every state tag introduced on this branch lands on every
metric of its target entity. These tests are tag-presence guards: if someone removes a
tag emission from _extract_host_tags / _extract_cluster_tags / _extract_vm_tags, the
exact metric that loses the tag is named in the failure rather than failing only the
specific assertions in test_hosts/test_vms/test_clusters that bundle the new tags into
HOST_TAGS / VM_TAGS / CLUSTER_TAGS.
"""

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME
from tests.metrics import (
    CLUSTER_BASIC_METRICS,
    CLUSTER_CAPACITY_METRICS,
    CLUSTER_STATS_METRICS_REQUIRED,
    HOST_BASIC_METRICS,
    HOST_CAPACITY_METRICS,
    HOST_STATS_METRICS_REQUIRED,
    HOST_STORAGE_METRICS,
    VM_BASIC_METRICS,
    VM_CAPACITY_METRICS,
    VM_STATS_METRICS_REQUIRED,
)

pytestmark = [pytest.mark.unit]

# The first host in the fixture has both maintenanceState and acropolisConnectionState set;
# the second host has only acropolisConnectionState. The new state tags are emitted only when
# the source field is present in the API response (defensive on missing fields), so per-tag
# coverage assertions scope to the entity instances whose source data is known to populate.


def _tag_keys(metric_obj):
    """Return the set of tag KEYS present on a metric (e.g., 'ntnx_power_state')."""
    return {t.split(":", 1)[0] for t in metric_obj.tags}


@pytest.fixture
def emitted(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Run the check once; tests below introspect the resulting aggregator."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    return aggregator


# ---------- Host: maintenance + connection state ----------


def _is_for_host(metric_obj, host_name: str) -> bool:
    return f"ntnx_host_name:{host_name}" in metric_obj.tags


def test_every_host_metric_carries_maintenance_state_when_present_in_source(emitted):
    """Hosts whose API response includes maintenanceState must carry ntnx_maintenance_state on every metric."""
    host_metrics = HOST_BASIC_METRICS + HOST_CAPACITY_METRICS + HOST_STATS_METRICS_REQUIRED
    missing = [
        (name, sorted(m.tags))
        for name in host_metrics
        for m in emitted.metrics(name)
        if _is_for_host(m, HOST_NAME) and "ntnx_maintenance_state" not in _tag_keys(m)
    ]
    assert not missing, f"Host metrics for {HOST_NAME} missing ntnx_maintenance_state: {missing}"


def test_every_host_metric_carries_connection_state(emitted):
    """Both fixture hosts have acropolisConnectionState, so every host metric must carry the tag."""
    host_metrics = HOST_BASIC_METRICS + HOST_CAPACITY_METRICS + HOST_STATS_METRICS_REQUIRED
    missing = [
        (name, sorted(m.tags))
        for name in host_metrics
        for m in emitted.metrics(name)
        if "ntnx_connection_state" not in _tag_keys(m)
    ]
    assert not missing, f"Host metrics missing ntnx_connection_state: {missing}"


# ---------- VM: power_state ----------


def test_every_vm_metric_carries_power_state(emitted):
    vm_metrics = VM_BASIC_METRICS + VM_CAPACITY_METRICS + VM_STATS_METRICS_REQUIRED
    missing = []
    for name in vm_metrics:
        for m in emitted.metrics(name):
            if "ntnx_power_state" not in _tag_keys(m):
                missing.append((name, sorted(m.tags)))
    assert not missing, f"VM metrics missing ntnx_power_state: {missing}"


# ---------- Cluster: operation_mode ----------


def test_every_cluster_metric_carries_operation_mode(emitted):
    cluster_metrics = CLUSTER_BASIC_METRICS + CLUSTER_CAPACITY_METRICS + CLUSTER_STATS_METRICS_REQUIRED
    missing = []
    for name in cluster_metrics:
        for m in emitted.metrics(name):
            if "ntnx_operation_mode" not in _tag_keys(m):
                missing.append((name, sorted(m.tags)))
    assert not missing, f"Cluster metrics missing ntnx_operation_mode: {missing}"


# ---------- Disk status: scoped to storage_* ----------


def test_storage_metrics_carry_disk_status(emitted):
    """Every host.storage_* metric emitted in the recorded fixture must have ntnx_disk_status."""
    missing = []
    for name in HOST_STORAGE_METRICS:
        metrics = emitted.metrics(name)
        if not metrics:
            continue
        for m in metrics:
            if "ntnx_disk_status" not in _tag_keys(m):
                missing.append((name, sorted(m.tags)))
    assert not missing, f"Storage metrics missing ntnx_disk_status: {missing}"


def test_non_storage_host_metrics_never_carry_disk_status(emitted):
    """ntnx_disk_status must only appear on host.storage_* metrics — not on cpu/memory/etc."""
    leaked = []
    non_storage = set(HOST_BASIC_METRICS + HOST_CAPACITY_METRICS + HOST_STATS_METRICS_REQUIRED) - HOST_STORAGE_METRICS
    for name in non_storage:
        for m in emitted.metrics(name):
            if "ntnx_disk_status" in _tag_keys(m):
                leaked.append((name, sorted(m.tags)))
    assert not leaked, f"Non-storage host metrics leaking ntnx_disk_status: {leaked}"
