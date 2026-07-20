# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock

import pytest

from datadog_checks.slurm import SlurmCheck
from datadog_checks.slurm.rest import (
    SlurmRestAPIClient,
    gpu_count_from_gres,
    is_number,
    iter_node_metrics,
    iter_partition_gpu_metrics,
    iter_partition_metrics,
    iter_sdiag_metrics,
    unwrap_number,
)

DIAG_PAYLOAD = {
    "statistics": {
        "server_thread_count": 3,
        "jobs_submitted": 10,
        "jobs_running": 2,
        "jobs_pending": 1,
        "schedule_cycle_last": 55,
        "schedule_cycle_max": 900,
        "schedule_cycle_total": 340,
        "schedule_cycle_mean": 9,
        "bf_backfilled_jobs": 7,
        "bf_cycle_counter": 4,
        "bf_queue_len": 5,
        "bf_active": False,  # boolean must be ignored
        "gettimeofday_latency": 12,  # unmapped must be ignored
    },
    "errors": [],
}

NODES_PAYLOAD = {
    "nodes": [
        {
            "name": "slinky-0",
            "cluster_name": "slurm_slurm",
            "partitions": ["all"],
            "state": ["IDLE", "DYNAMIC_NORM"],
            "cpus": 16,
            "alloc_cpus": 4,
            "alloc_idle_cpus": 12,
            "cpu_load": 305,  # slurmrestd scales x100 -> load 3.05
            "real_memory": 62919,
            "alloc_memory": 2048,
            "free_mem": {"set": True, "infinite": False, "number": 2296},
            "temporary_disk": 0,
            "active_features": ["cpu"],
        }
    ],
    "errors": [],
}

PARTITIONS_PAYLOAD = {
    "partitions": [
        {
            "name": "all",
            "cluster": "slurm_slurm",
            "nodes": {"total": 1, "configured": "slinky-0"},
            "cpus": {"total": 16},
        }
    ],
    "errors": [],
}


def test_unwrap_number():
    assert unwrap_number(42) == 42
    assert unwrap_number({"set": True, "infinite": False, "number": 7}) == 7
    assert unwrap_number({"set": False, "infinite": False, "number": 0}) is None
    assert unwrap_number({"set": True, "infinite": True, "number": 0}) is None


def test_is_number_rejects_bool():
    assert is_number(3) and is_number(1.5)
    assert not is_number(True) and not is_number(None) and not is_number("x")


def test_iter_sdiag_metrics_maps_known_keys():
    metrics = {name: value for name, value, _tags in iter_sdiag_metrics(DIAG_PAYLOAD)}
    assert metrics["sdiag.server_thread_count"] == 3
    assert metrics["sdiag.jobs_submitted"] == 10
    assert metrics["sdiag.last_cycle"] == 55
    assert metrics["sdiag.total_cycles"] == 340
    assert metrics["sdiag.mean_cycle"] == 9
    assert metrics["sdiag.backfill.total_jobs_since_start"] == 7
    assert metrics["sdiag.backfill.total_cycles"] == 4
    assert metrics["sdiag.backfill.last_queue_length"] == 5
    # Booleans and unmapped keys are not emitted.
    assert not any(name.endswith("bf_active") for name in metrics)


def test_iter_sdiag_metrics_handles_empty():
    assert list(iter_sdiag_metrics(None)) == []
    assert list(iter_sdiag_metrics({})) == []


def test_iter_node_metrics():
    emitted = list(iter_node_metrics(NODES_PAYLOAD))
    metrics = {name: value for name, value, _tags in emitted}
    assert metrics["node.cpu.total"] == 16
    assert metrics["node.cpu.allocated"] == 4
    assert metrics["node.cpu.idle"] == 12
    assert metrics["node.cpu_load"] == pytest.approx(3.05)  # scaled down from 305
    assert metrics["node.memory"] == 62919
    assert metrics["node.alloc_mem"] == 2048
    assert metrics["node.free_mem"] == 2296  # unwrapped
    assert metrics["node.info"] == 1
    # node.cpu.other is intentionally not emitted in REST mode (structurally ~0, misleading).
    assert "node.cpu.other" not in metrics

    tags_by_metric = {name: t for name, _v, t in emitted}
    # Scalar metrics carry identity + partition, but NOT state (state lives on node.info, per CLI).
    scalar_tags = tags_by_metric["node.cpu.total"]
    assert "slurm_node_name:slinky-0" in scalar_tags
    assert "slurm_cluster_name:slurm_slurm" in scalar_tags
    assert "slurm_partition_name:all" in scalar_tags
    assert not any(t.startswith("slurm_node_state:") for t in scalar_tags)
    # node.info carries the full (joined) state.
    info_tags = tags_by_metric["node.info"]
    assert "slurm_node_state:idle,dynamic_norm" in info_tags


def test_iter_node_metrics_multiple_partitions_emits_per_partition():
    payload = {"nodes": [{"name": "n0", "cpus": 8, "partitions": ["a", "b"], "state": ["IDLE"]}]}
    emitted = [(m, tuple(t)) for m, _v, t in iter_node_metrics(payload) if m == "node.cpu.total"]
    # One series per (node, partition), each with a single-valued partition tag.
    assert len(emitted) == 2
    part_tags = {next(t for t in tags if t.startswith("slurm_partition_name:")) for _m, tags in emitted}
    assert part_tags == {"slurm_partition_name:a", "slurm_partition_name:b"}


def test_iter_node_metrics_missing_fields():
    # A node missing most fields must not crash and must still emit node.info.
    emitted = list(iter_node_metrics({"nodes": [{"name": "n0"}]}))
    metrics = {name for name, _v, _t in emitted}
    assert "node.info" in metrics
    assert "node.cpu.total" not in metrics  # cpus missing -> skipped, no crash


def test_iter_node_metrics_handles_wrapped_numeric_fields():
    # Some slurmrestd builds/data_parser versions wrap fields that are plain ints on others
    # (see NODES_PAYLOAD above, e.g. free_mem). Every numeric node field must go through
    # unwrap_number, not just the ones observed wrapped in our reference cluster -- otherwise a
    # differently-wrapped field is silently dropped (is_number(dict) is False) instead of parsed.
    payload = {
        "nodes": [
            {
                "name": "n0",
                "cpus": {"set": True, "infinite": False, "number": 8},
                "alloc_cpus": {"set": True, "infinite": False, "number": 2},
                "alloc_idle_cpus": {"set": True, "infinite": False, "number": 6},
                "real_memory": {"set": True, "infinite": False, "number": 32000},
                "alloc_memory": {"set": True, "infinite": False, "number": 1024},
                "state": ["IDLE"],
            }
        ]
    }
    metrics = {name: value for name, value, _tags in iter_node_metrics(payload)}
    assert metrics["node.cpu.total"] == 8
    assert metrics["node.cpu.allocated"] == 2
    assert metrics["node.cpu.idle"] == 6
    assert metrics["node.memory"] == 32000
    assert metrics["node.alloc_mem"] == 1024


def test_iter_partition_metrics():
    emitted = list(iter_partition_metrics(PARTITIONS_PAYLOAD))
    metrics = {name: (value, tags) for name, value, tags in emitted}
    assert metrics["partition.nodes.count"][0] == 1
    assert "slurm_partition_name:all" in metrics["partition.nodes.count"][1]
    assert metrics["partition.info"][0] == 1
    assert "slurm_partition_node_list:slinky-0" in metrics["partition.info"][1]


def test_iter_partition_metrics_handles_wrapped_node_total():
    payload = {
        "partitions": [
            {
                "name": "all",
                "nodes": {"total": {"set": True, "infinite": False, "number": 3}, "configured": "n0,n1,n2"},
            }
        ]
    }
    metrics = {name: value for name, value, _tags in iter_partition_metrics(payload)}
    assert metrics["partition.nodes.count"] == 3


def test_gpu_count_from_gres():
    # No type (slurmrestd's observed shape), with type, and a used-string IDX suffix.
    assert gpu_count_from_gres("gpu:1") == (None, 1)
    assert gpu_count_from_gres("gpu:0") == (None, 0)
    assert gpu_count_from_gres("gpu:tesla_t4:4") == ("tesla_t4", 4)
    assert gpu_count_from_gres("gpu:tesla_t4:2(IDX:0-1)") == ("tesla_t4", 2)
    # Multi-GRES: the gpu entry is picked out regardless of position.
    assert gpu_count_from_gres("mps:100,gpu:3") == (None, 3)
    # No gpu / empty / unparseable.
    assert gpu_count_from_gres("") == (None, None)
    assert gpu_count_from_gres(None) == (None, None)
    assert gpu_count_from_gres("mps:100") == (None, None)


def test_iter_node_metrics_gpu_disabled_by_default():
    payload = {"nodes": [{"name": "n0", "partitions": ["all"], "gres": "gpu:4", "gres_used": "gpu:1"}]}
    metrics = {name for name, _value, _tags in iter_node_metrics(payload)}
    assert "node.gpu_total" not in metrics
    assert "node.gpu_used" not in metrics


def test_iter_node_metrics_gpu():
    payload = {
        "nodes": [
            {
                "name": "n0",
                "cluster_name": "c",
                "partitions": ["all"],
                "gres": "gpu:tesla_t4:4",
                "gres_used": "gpu:tesla_t4:1(IDX:0)",
            }
        ]
    }
    emitted = {name: (value, tags) for name, value, tags in iter_node_metrics(payload, collect_gpu=True)}
    assert emitted["node.gpu_total"][0] == 4
    assert emitted["node.gpu_used"][0] == 1
    assert "slurm_node_gpu_type:tesla_t4" in emitted["node.gpu_total"][1]
    assert "slurm_node_name:n0" in emitted["node.gpu_total"][1]


def test_iter_partition_gpu_metrics_aggregates_across_nodes():
    # Two nodes in partition "all", one also in "gpu"; partition totals are summed from node gres.
    payload = {
        "nodes": [
            {"name": "n0", "cluster_name": "c", "partitions": ["all", "gpu"], "gres": "gpu:4", "gres_used": "gpu:1"},
            {"name": "n1", "cluster_name": "c", "partitions": ["all"], "gres": "gpu:2", "gres_used": "gpu:2"},
            {"name": "n2", "cluster_name": "c", "partitions": ["all"]},  # no gres -> contributes nothing
        ]
    }
    emitted = {}
    for name, value, tags in iter_partition_gpu_metrics(payload):
        emitted[(name, tuple(t for t in tags if t.startswith("slurm_partition_name")))] = value

    assert emitted[("partition.gpu_total", ("slurm_partition_name:all",))] == 6
    assert emitted[("partition.gpu_used", ("slurm_partition_name:all",))] == 3
    assert emitted[("partition.gpu_total", ("slurm_partition_name:gpu",))] == 4
    assert emitted[("partition.gpu_used", ("slurm_partition_name:gpu",))] == 1


def test_iter_partition_gpu_metrics_no_gpu_nodes_emits_nothing():
    payload = {"nodes": [{"name": "n0", "partitions": ["all"]}, {"name": "n1", "partitions": ["all"]}]}
    assert list(iter_partition_gpu_metrics(payload)) == []


def test_rest_client_returns_none_on_exception():
    http = MagicMock()
    http.get.side_effect = ConnectionError("refused")
    client = SlurmRestAPIClient(http, "http://x:6820", "v0.0.42", MagicMock())
    assert client.get("nodes") is None


def test_rest_client_returns_none_when_payload_has_errors():
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"errors": [{"error": "Protocol authentication error"}]}
    http.get.return_value = response
    client = SlurmRestAPIClient(http, "http://x:6820", "v0.0.42", MagicMock())
    assert client.get("nodes") is None


def test_rest_client_returns_none_on_non_dict_payload():
    # slurmrestd/proxy returning a JSON list or scalar must not raise (never-raise guarantee).
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = [1, 2, 3]
    http.get.return_value = response
    client = SlurmRestAPIClient(http, "http://x:6820", "v0.0.42", MagicMock())
    assert client.get("nodes") is None


def test_rest_client_sends_token_header_and_returns_payload():
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"nodes": [], "errors": []}
    http.get.return_value = response
    client = SlurmRestAPIClient(http, "http://x:6820/", "v0.0.42", MagicMock())
    client.token = "jwt-abc"
    assert client.get("nodes") == {"nodes": [], "errors": []}
    _args, kwargs = http.get.call_args
    assert kwargs["extra_headers"]["X-SLURM-USER-TOKEN"] == "jwt-abc"


def test_rest_client_omits_user_header_by_default():
    # Direct per-user JWTs (e.g. via `scontrol token`) already identify the user via the
    # token's own claims -- X-SLURM-USER-NAME must not be sent unless explicitly configured.
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"nodes": [], "errors": []}
    http.get.return_value = response
    client = SlurmRestAPIClient(http, "http://x:6820/", "v0.0.42", MagicMock())
    client.token = "jwt-abc"
    client.get("nodes")
    _args, kwargs = http.get.call_args
    assert "X-SLURM-USER-NAME" not in kwargs["extra_headers"]


def test_rest_client_sends_user_header_when_configured():
    # Needed behind an authenticating proxy that reuses one privileged token for multiple users.
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"nodes": [], "errors": []}
    http.get.return_value = response
    client = SlurmRestAPIClient(http, "http://x:6820/", "v0.0.42", MagicMock())
    client.token = "jwt-abc"
    client.user = "datadog"
    client.get("nodes")
    _args, kwargs = http.get.call_args
    assert kwargs["extra_headers"]["X-SLURM-USER-NAME"] == "datadog"
    assert kwargs["extra_headers"]["X-SLURM-USER-TOKEN"] == "jwt-abc"


def test_get_rest_token_from_file(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("jwt-from-file\n")
    check = SlurmCheck(
        "slurm",
        {},
        [{"slurm_rest_api_url": "http://x:6820", "slurm_rest_api_token_file": str(token_file)}],
    )
    assert check._get_rest_token() == "jwt-from-file"


def test_get_rest_token_missing_file_returns_none():
    check = SlurmCheck(
        "slurm",
        {},
        [{"slurm_rest_api_url": "http://x:6820", "slurm_rest_api_token_file": "/no/such/token"}],
    )
    assert check._get_rest_token() is None


def test_cli_mode_when_rest_url_absent():
    check = SlurmCheck("slurm", {}, [{}])
    assert check.use_rest_api is False


@pytest.mark.parametrize("ping_ok", [True, False])
def test_check_rest_mode(aggregator, dd_run_check, ping_ok):
    instance = {
        "slurm_rest_api_url": "http://slurm-restapi:6820",
        "slurm_rest_api_token": "jwt-abc",
        "collect_sinfo_stats": True,
        "collect_sdiag_stats": True,
        "sinfo_collection_level": 2,  # level >= 2 also collects node metrics
    }
    check = SlurmCheck("slurm", {}, [instance])
    assert check.use_rest_api is True

    def fake_get(resource):
        if not ping_ok:
            return None
        return {
            "ping": {"errors": []},
            "diag": DIAG_PAYLOAD,
            "nodes": NODES_PAYLOAD,
            "partitions": PARTITIONS_PAYLOAD,
        }.get(resource)

    check.rest_client = MagicMock()
    check.rest_client.get.side_effect = fake_get

    dd_run_check(check)

    if ping_ok:
        aggregator.assert_service_check("slurm.rest.can_connect", SlurmCheck.OK)
        aggregator.assert_metric("slurm.sdiag.jobs_submitted", value=10)
        aggregator.assert_metric("slurm.partition.nodes.count", value=1)
        aggregator.assert_metric("slurm.sinfo.partition.enabled", value=1)
        aggregator.assert_metric("slurm.sinfo.node.enabled", value=1)
        aggregator.assert_metric("slurm.node.cpu.total", value=16)
        aggregator.assert_metric("slurm.node.cpu_load", value=pytest.approx(3.05))
        aggregator.assert_metric("slurm.node.free_mem", value=2296)
        aggregator.assert_metric("slurm.node.info", value=1)
    else:
        aggregator.assert_service_check("slurm.rest.can_connect", SlurmCheck.CRITICAL)
        assert not aggregator.metric_names
