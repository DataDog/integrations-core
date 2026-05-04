# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

pytestmark = [pytest.mark.unit]


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
    """All recognized fields present produce all tags; state-tag VALUES are lowercased on emission."""
    host = {
        "hostName": "h1",
        "hostType": "HYPER_CONVERGED",
        "maintenanceState": "Entering_Maintenance_Mode",
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
        "ntnx_connection_state:disconnected",
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
    """operationMode is lowercased on emission."""
    tags = monitor._extract_cluster_tags({"name": "c1", "config": {"operationMode": "STAND_ALONE"}})
    assert "ntnx_operation_mode:stand_alone" in tags


# ---------- _extract_vm_tags ----------


def test_vm_tags_power_state_lowercased(monitor):
    """PAUSED is lowercased on emission."""
    tags = monitor._extract_vm_tags({"name": "vm1", "powerState": "PAUSED"})
    assert "ntnx_power_state:paused" in tags


def test_vm_tags_no_power_state_falls_back_to_unknown(monitor):
    """A VM without powerState gets ntnx_power_state:unknown so dashboards/monitors do not lose rows."""
    tags = monitor._extract_vm_tags({"name": "vm1"})
    assert "ntnx_power_state:unknown" in tags


def test_vm_tags_empty_power_state_falls_back_to_unknown(monitor):
    """Empty-string powerState falls back to unknown for the same reason."""
    tags = monitor._extract_vm_tags({"name": "vm1", "powerState": ""})
    assert "ntnx_power_state:unknown" in tags


@pytest.mark.parametrize(
    "vm,expected_tag",
    [
        ({"name": "vm1", "powerState": 42}, "ntnx_power_state:unknown"),
        ({"name": "vm1", "powerState": True}, "ntnx_power_state:unknown"),
        ({"name": "vm1", "powerState": ["ON"]}, "ntnx_power_state:unknown"),
    ],
)
def test_vm_tags_non_string_power_state_falls_back_safely(monitor, vm, expected_tag):
    """A non-string powerState (defensive against API misbehavior) does not crash; falls back to unknown."""
    tags = monitor._extract_vm_tags(vm)
    assert expected_tag in tags


@pytest.mark.parametrize(
    "host_field,host_value,expected_tag_key",
    [
        ("maintenanceState", 42, "ntnx_maintenance_state"),
        ("maintenanceState", True, "ntnx_maintenance_state"),
    ],
)
def test_host_tags_non_string_state_does_not_crash(monitor, host_field, host_value, expected_tag_key):
    """Non-string host state values are dropped, not raised."""
    tags = monitor._extract_host_tags({host_field: host_value})
    assert all(expected_tag_key not in t for t in tags)


def test_cluster_tags_non_string_operation_mode_dropped(monitor):
    """Non-string operationMode values do not crash and produce no tag."""
    tags = monitor._extract_cluster_tags({"name": "c1", "config": {"operationMode": 42}})
    assert all("ntnx_operation_mode" not in t for t in tags)


# ---------- _extract_vm_disk_capacity_bytes ----------


@pytest.mark.parametrize(
    "vm,expected",
    [
        ({}, 0),
        ({"disks": None}, 0),
        ({"disks": []}, 0),
        ({"disks": [{"backingInfo": {"diskSizeBytes": 100}}]}, 100),
        ({"disks": [{"backingInfo": {"diskSizeBytes": 100}}, {"backingInfo": {"diskSizeBytes": 50}}]}, 150),
        # Defensive: missing backingInfo / diskSizeBytes contributes zero, doesn't raise.
        ({"disks": [{"backingInfo": {"diskSizeBytes": 100}}, {"backingInfo": {}}]}, 100),
        ({"disks": [{"backingInfo": {"diskSizeBytes": 100}}, {}]}, 100),
        # Non-dict entries are skipped, not raised.
        ({"disks": [None, "junk", 42, {"backingInfo": {"diskSizeBytes": 50}}]}, 50),
    ],
)
def test_extract_vm_disk_capacity_bytes(monitor, vm, expected):
    assert monitor._extract_vm_disk_capacity_bytes(vm) == expected
