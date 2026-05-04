# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from types import SimpleNamespace

import pytest

from datadog_checks.nutanix import NutanixCheck
from datadog_checks.nutanix.infrastructure_monitor import InfrastructureMonitor
from tests.constants import HOST_NAME, HOST_TAGS

pytestmark = [pytest.mark.unit]


@pytest.fixture
def monitor():
    """Return an InfrastructureMonitor with a minimal check stub (sufficient for pure-logic tests)."""
    check_stub = SimpleNamespace(pc_ip="10.0.0.197")
    return InfrastructureMonitor(check_stub)


@pytest.mark.parametrize(
    "disks,expected",
    [
        ([], None),
        ([{"status": "NORMAL"}], "normal"),
        ([{"status": "DETACHABLE"}], "degraded"),
        ([{"status": "MARKED_FOR_REMOVAL_BUT_NOT_DETACHABLE"}], "degraded"),
        ([{"status": "DATA_MIGRATION_INITIATED"}], "degraded"),
        ([{"status": "$UNKNOWN"}], None),
        ([{"status": "$REDACTED"}], None),
        ([{"status": "NORMAL"}, {"status": "$UNKNOWN"}], "normal"),
        ([{"status": "NORMAL"}, {"status": "DETACHABLE"}], "degraded"),
        ([{"extId": "no-status-field"}], None),
        ([{"status": ""}], None),
        # Forward-compat: a future enum value we don't recognize must not crash
        # and must not be classified as either degraded or normal.
        ([{"status": "SOME_FUTURE_STATUS"}], None),
        ([{"status": "NORMAL"}, {"status": "SOME_FUTURE_STATUS"}], "normal"),
        # Malformed inputs: non-dict entries from a misbehaving API are skipped, not raised.
        ([None], None),
        ([None, None], None),
        ("not-a-list-but-iterable", None),
        ([{"status": "NORMAL"}, None, "weird-string", 42], "normal"),
        ([{"status": "DETACHABLE"}, None], "degraded"),
    ],
)
def test_aggregate_disk_status(monitor, disks, expected):
    assert monitor._aggregate_disk_status(disks) == expected


def test_get_disk_status_storage_tags_unknown_host_returns_empty(monitor):
    """Hosts not in the disk cache yield no extra tags (no ntnx_disk_status)."""
    assert monitor._get_disk_status_storage_tags("not-in-cache") == {}


def test_get_disk_status_storage_tags_returns_independent_lists(monitor):
    """Each storage-key entry must be its own list (no shared reference)."""
    monitor._disks_by_host = {"h1": [{"status": "NORMAL"}]}
    tags = monitor._get_disk_status_storage_tags("h1")

    assert set(tags) == {
        "freePhysicalStorageBytes",
        "logicalStorageUsageBytes",
        "storageCapacityBytes",
        "storageUsageBytes",
    }
    keys = list(tags)
    # Mutating one entry must not leak into the others.
    tags[keys[0]].append("ntnx_extra:x")
    for key in keys[1:]:
        assert tags[key] == ["ntnx_disk_status:normal"]


def test_build_disks_by_host_cache_skips_disks_without_node_ext_id(monitor, mocker):
    """Disks lacking nodeExtId are silently dropped, not assigned to "" or any host."""
    mocker.patch.object(
        monitor,
        "_list_all_disks",
        return_value=[
            {"status": "NORMAL", "nodeExtId": "host-a"},
            {"status": "NORMAL"},
            {"status": "NORMAL", "nodeExtId": ""},
            {"status": "DETACHABLE", "nodeExtId": "host-b"},
        ],
    )
    monitor._build_disks_by_host_cache()

    assert set(monitor._disks_by_host) == {"host-a", "host-b"}
    assert "" not in monitor._disks_by_host


def test_build_disks_by_host_cache_skips_non_dict_entries(monitor, mocker):
    """Malformed API responses (None, strings, ints) must not crash the cache build."""
    mocker.patch.object(
        monitor,
        "_list_all_disks",
        return_value=[
            None,
            "not-a-disk",
            42,
            {"status": "NORMAL", "nodeExtId": "host-a"},
            None,
        ],
    )
    monitor._build_disks_by_host_cache()

    assert monitor._disks_by_host == {"host-a": [{"status": "NORMAL", "nodeExtId": "host-a"}]}


def test_disks_endpoint_failure_still_emits_storage_metrics_without_tag(
    dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """If /config/disks raises, storage metrics still report; just without ntnx_disk_status."""
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_all_disks",
        side_effect=RuntimeError("boom"),
    )
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.storage_capacity", at_least=1, tags=HOST_TAGS, hostname=HOST_NAME)
    for metric in aggregator.metrics("nutanix.host.storage_capacity"):
        assert not any(t.startswith("ntnx_disk_status:") for t in metric.tags)


def test_degraded_disk_status_flows_to_storage_metrics(dd_run_check, aggregator, mock_instance, mock_http_get, mocker):
    """A DETACHABLE disk on a host yields ntnx_disk_status:degraded on its storage metrics."""
    host_id = "d8787814-4fe8-4ba5-931f-e1ee31c294a6"
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_all_disks",
        return_value=[{"nodeExtId": host_id, "status": "DETACHABLE"}],
    )
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.host.storage_capacity",
        at_least=1,
        tags=HOST_TAGS + ['ntnx_disk_status:degraded'],
        hostname=HOST_NAME,
    )
