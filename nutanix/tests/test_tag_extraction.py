# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from types import SimpleNamespace

import pytest

from datadog_checks.nutanix.infrastructure_monitor import InfrastructureMonitor

pytestmark = [pytest.mark.unit]


@pytest.fixture
def monitor():
    """Stub check is enough — extract_*_tags methods only call check.extract_category_tags."""
    check_stub = SimpleNamespace(
        pc_ip="10.0.0.197",
        extract_category_tags=lambda _entity: [],
    )
    return InfrastructureMonitor(check_stub)


# ---------- _extract_host_tags ----------


def test_host_tags_omitted_when_fields_missing(monitor):
    """A bare host should produce only ntnx_type:host (no maintenance/connection tags)."""
    tags = monitor._extract_host_tags({})
    assert tags == ["ntnx_type:host"]


def test_host_tags_no_hypervisor_block(monitor):
    """Host with no hypervisor block should not raise and should emit no hypervisor-derived tags."""
    tags = monitor._extract_host_tags({"hostName": "h1", "maintenanceState": "normal"})
    assert "ntnx_connection_state" not in " ".join(tags)
    assert "ntnx_hypervisor_name" not in " ".join(tags)
    assert "ntnx_maintenance_state:normal" in tags


def test_host_tags_full(monitor):
    """All recognized fields present produce all tags."""
    host = {
        "hostName": "h1",
        "hostType": "HYPER_CONVERGED",
        "maintenanceState": "entering_maintenance_mode",
        "hypervisor": {
            "fullName": "AHV 10.3",
            "type": "AHV",
            "acropolisConnectionState": "DISCONNECTED",
        },
    }
    tags = set(monitor._extract_host_tags(host))
    assert tags == {
        "ntnx_type:host",
        "ntnx_host_name:h1",
        "ntnx_host_type:HYPER_CONVERGED",
        "ntnx_maintenance_state:entering_maintenance_mode",
        "ntnx_hypervisor_name:AHV 10.3",
        "ntnx_hypervisor_type:AHV",
        "ntnx_connection_state:DISCONNECTED",
    }


def test_host_tags_empty_string_fields_dropped(monitor):
    """Empty-string field values are not emitted as tags (truthy check)."""
    host = {
        "maintenanceState": "",
        "hypervisor": {"acropolisConnectionState": ""},
    }
    tags = monitor._extract_host_tags(host)
    assert all("ntnx_maintenance_state" not in t for t in tags)
    assert all("ntnx_connection_state" not in t for t in tags)


# ---------- _extract_cluster_tags ----------


def test_cluster_tags_omits_operation_mode_when_missing(monitor):
    """Cluster with no config block emits no ntnx_operation_mode tag."""
    tags = monitor._extract_cluster_tags({"name": "c1"})
    assert "ntnx_cluster_name:c1" in tags
    assert all("ntnx_operation_mode" not in t for t in tags)


def test_cluster_tags_omits_operation_mode_when_config_present_but_empty(monitor):
    """Cluster with config={} emits no ntnx_operation_mode tag."""
    tags = monitor._extract_cluster_tags({"name": "c1", "config": {}})
    assert all("ntnx_operation_mode" not in t for t in tags)


def test_cluster_tags_with_operation_mode(monitor):
    tags = monitor._extract_cluster_tags({"name": "c1", "config": {"operationMode": "STAND_ALONE"}})
    assert "ntnx_operation_mode:STAND_ALONE" in tags


# ---------- _extract_vm_tags ----------


def test_vm_tags_paused_power_state(monitor):
    """PAUSED is preserved verbatim as the tag value."""
    tags = monitor._extract_vm_tags({"name": "vm1", "powerState": "PAUSED"})
    assert "ntnx_power_state:PAUSED" in tags


def test_vm_tags_no_power_state(monitor):
    """A VM without powerState produces no ntnx_power_state tag (does not raise)."""
    tags = monitor._extract_vm_tags({"name": "vm1"})
    assert all("ntnx_power_state" not in t for t in tags)


def test_vm_tags_empty_power_state(monitor):
    """Empty-string powerState should not produce a tag."""
    tags = monitor._extract_vm_tags({"name": "vm1", "powerState": ""})
    assert all("ntnx_power_state" not in t for t in tags)
