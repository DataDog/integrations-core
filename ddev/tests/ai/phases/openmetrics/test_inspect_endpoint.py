# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import json
import os

import httpx
import pytest
from prometheus_client import Metric
from prometheus_client.parser import text_string_to_metric_families as parse_prometheus
from pydantic import ValidationError

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import CheckpointConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.openmetrics import inspect_endpoint as inspect_endpoint_module
from ddev.ai.phases.openmetrics.inspect_endpoint import (
    EndpointInspectionError,
    EndpointResult,
    EndpointSpec,
    InspectEndpointPhase,
    InspectInput,
    _build_jsonl_rows,
    _build_memory_text,
    _parse_exposition,
    normalize_endpoint_name,
)
from ddev.ai.runtime.checkpoints import CheckpointManager, CheckpointTokenInfo, FailedCheckpoint, SuccessCheckpoint
from ddev.event_bus.exceptions import MessageProcessingError

ENDPOINT_URL = "http://example.test:9100/metrics"
ENDPOINT_NAME = "main"
PHASE_ID = "inspect_endpoint"

PROMETHEUS_BODY = """\
# HELP http_requests_total Total HTTP requests.
# TYPE http_requests_total counter
http_requests_total{method="GET",code="200"} 1027
# HELP process_resident_memory_bytes Resident memory in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 1.2e+08
# HELP request_duration_seconds Request latency.
# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{le="0.1"} 3
request_duration_seconds_bucket{le="0.5"} 5
request_duration_seconds_bucket{le="+Inf"} 7
request_duration_seconds_sum 1.5
request_duration_seconds_count 7
"""

OPENMETRICS_BODY = """\
# TYPE http_requests counter
# HELP http_requests Total HTTP requests.
# UNIT http_requests requests
http_requests_total{method="GET",code="200"} 1027
# TYPE process_resident_memory_bytes gauge
# UNIT process_resident_memory_bytes bytes
# HELP process_resident_memory_bytes Resident memory in bytes.
process_resident_memory_bytes 1.2e+08
# EOF
"""

OPENMETRICS_BODY_CLEAN = """\
# TYPE http_requests counter
# HELP http_requests Total HTTP requests.
http_requests_total{method="GET",code="200"} 1027
# TYPE process_resident_memory_bytes gauge
# HELP process_resident_memory_bytes Resident memory in bytes.
process_resident_memory_bytes 1.2e+08
# TYPE request_duration_seconds summary
# HELP request_duration_seconds Request latency.
request_duration_seconds{quantile="0.5"} 0.04
request_duration_seconds{quantile="0.9"} 0.09
request_duration_seconds_sum 1.5
request_duration_seconds_count 7
# EOF
"""

OPENMETRICS_BODY_WITH_UNIT = """\
# TYPE request_duration_seconds gauge
# HELP request_duration_seconds Request latency snapshot.
# UNIT request_duration_seconds seconds
request_duration_seconds 0.42
# EOF
"""

# A distinct second body, for multi-endpoint tests where the two catalogs must differ.
PROMETHEUS_BODY_SECOND = """\
# HELP queue_depth Current queue depth.
# TYPE queue_depth gauge
queue_depth{shard="a"} 3
# HELP jobs_processed_total Total jobs processed.
# TYPE jobs_processed_total counter
jobs_processed_total{shard="a"} 42
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flow_dir(tmp_path):
    return tmp_path


@pytest.fixture
def message_queue():
    return asyncio.Queue()


def _inspect_input_var(*pairs: tuple[str, str]) -> dict[str, str]:
    payload = {"endpoints": [{"name": n, "url": u} for n, u in pairs]}
    return {"inspect_input": json.dumps(payload)}


def _make_phase(
    flow_dir,
    message_queue,
    *,
    phase_id: str = PHASE_ID,
    runtime_variables: dict[str, str] | None = None,
) -> tuple[InspectEndpointPhase, CheckpointManager]:
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    context = FlowContext(
        runtime_variables=(
            runtime_variables if runtime_variables is not None else _inspect_input_var((ENDPOINT_NAME, ENDPOINT_URL))
        ),
        flow_variables={},
    )
    phase = InspectEndpointPhase(
        phase_id=phase_id,
        dependencies=[],
        config=PhaseConfig(name=phase_id),
        checkpoint_manager=checkpoint_manager,
        context=context,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


def _install_mock_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient inside the phase module to use a MockTransport handler."""
    real_client_cls = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(inspect_endpoint_module.httpx, "AsyncClient", factory)


def _ok_handler(status: int, body: str, content_type: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, content=body.encode("utf-8"), headers={"Content-Type": content_type})

    return handler


def _raising_handler(exc: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


def _multi_handler(bodies_by_url: dict[str, tuple[int, str, str]]):
    """Dispatch by request URL so one mocked run can serve a different body per endpoint.

    A value may also be an ``Exception`` to raise (e.g. a timeout) for that URL.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        entry = bodies_by_url[str(request.url)]
        if isinstance(entry, Exception):
            raise entry
        status, body, ct = entry
        return httpx.Response(status_code=status, content=body.encode("utf-8"), headers={"Content-Type": ct})

    return handler


def _jsonl_path(flow_dir, name: str = ENDPOINT_NAME):
    return flow_dir / f"{PHASE_ID}_{name}_metrics.jsonl"


def _exposition_path(flow_dir, name: str = ENDPOINT_NAME):
    return flow_dir / f"{PHASE_ID}_{name}_exposition.txt"


def _read_jsonl(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _read_header(path) -> dict:
    return _read_jsonl(path)[0]


def _read_family_rows(path) -> list[dict]:
    return _read_jsonl(path)[1:]


def _endpoint_data(checkpoint, index: int = 0) -> dict:
    return checkpoint.phase_data["endpoints"][index]


class _Sample:
    """Minimal Sample stand-in for the label-union unit test."""

    def __init__(self, name: str, labels: dict[str, str], value: float):
        self.name = name
        self.labels = labels
        self.value = value


# ---------------------------------------------------------------------------
# Phase happy paths
# ---------------------------------------------------------------------------


async def test_success_with_prometheus_body(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(
        monkeypatch,
        _ok_handler(200, PROMETHEUS_BODY, "text/plain; version=0.0.4; charset=utf-8"),
    )
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    expected_families = list(parse_prometheus(PROMETHEUS_BODY))

    memory = mgr.memory_content(PHASE_ID)
    assert ENDPOINT_URL in memory
    assert "HTTP status:** 200" in memory

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    endpoint = _endpoint_data(checkpoint)
    assert endpoint["exposition_format"] == "prometheus"
    assert endpoint["metric_count"] == len(expected_families)
    assert "sample_metric_names" not in endpoint
    assert endpoint["status_code"] == 200
    assert endpoint["url"] == ENDPOINT_URL
    assert endpoint["name"] == ENDPOINT_NAME
    assert checkpoint.tokens == CheckpointTokenInfo(total_input=0, total_output=0)


async def test_success_with_openmetrics_body(flow_dir, message_queue, monkeypatch):
    content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
    _install_mock_transport(monkeypatch, _ok_handler(200, OPENMETRICS_BODY_CLEAN, content_type))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    endpoint = _endpoint_data(checkpoint)
    assert endpoint["exposition_format"] == "openmetrics"
    assert endpoint["content_type"] == content_type
    assert endpoint["metric_count"] >= 1


# ---------------------------------------------------------------------------
# Phase failure paths
# ---------------------------------------------------------------------------


async def _assert_phase_fails(phase, mgr, message_queue, *, error_contains: str):
    """Run process_message, expect failure, drive on_error like the framework would."""
    trigger = PhaseTrigger(id="start", phase_id=None)
    try:
        await phase.process_message(trigger)
    except Exception as raised:
        wrapped = MessageProcessingError(phase._phase_id, trigger, raised)
        await phase.on_error(wrapped)
        checkpoint = mgr.read()[phase._phase_id]
        assert isinstance(checkpoint, FailedCheckpoint)
        assert error_contains.lower() in checkpoint.error.lower()
        msg = message_queue.get_nowait()
        assert isinstance(msg, PhaseFailedMessage)
        assert error_contains.lower() in msg.error.lower()
        return raised
    pytest.fail(f"Expected process_message() to raise; error should contain {error_contains!r}")


async def test_failure_non_200_status(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(503, "service unavailable", "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="HTTP 503")


async def test_failure_body_is_html(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, "<html>not metrics</html>", "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="not valid prometheus exposition")


async def test_failure_body_is_json(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, '{"hello": "world"}', "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="prometheus")


async def test_failure_zero_families(flow_dir, message_queue, monkeypatch):
    body = "\n\n# just a stray comment, not a HELP/TYPE\n\n"
    _install_mock_transport(monkeypatch, _ok_handler(200, body, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="zero metric families")


async def test_failure_openmetrics_missing_eof(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(
        monkeypatch,
        _ok_handler(200, PROMETHEUS_BODY, "application/openmetrics-text; version=1.0.0"),
    )
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="not valid openmetrics exposition")


async def test_failure_timeout(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _raising_handler(httpx.TimeoutException("slow")))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="timed out")


async def test_failure_request_error(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _raising_handler(httpx.ConnectError("refused")))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="request failed")


async def test_failure_missing_inspect_input(flow_dir, message_queue):
    phase, mgr = _make_phase(flow_dir, message_queue, runtime_variables={})

    trigger = PhaseTrigger(id="start", phase_id=None)
    with pytest.raises(ConfigError, match="inspect_input"):
        await phase.process_message(trigger)

    wrapped = MessageProcessingError(phase._phase_id, trigger, ConfigError("inspect_input required"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, FailedCheckpoint)
    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def test_validate_config_rejects_agent():
    with pytest.raises(ConfigError, match="must not declare 'agent'"):
        InspectEndpointPhase.validate_config("p", PhaseConfig(name="p", agent="x"))


def test_validate_config_rejects_tasks():
    config = PhaseConfig(name="p", tasks=[TaskConfig(name="t", prompt="hi")])
    with pytest.raises(ConfigError, match="must not declare 'tasks'"):
        InspectEndpointPhase.validate_config("p", config)


def test_validate_config_rejects_checkpoint():
    config = PhaseConfig(name="p", checkpoint=CheckpointConfig(memory_prompt="x"))
    with pytest.raises(ConfigError, match="must not declare 'checkpoint'"):
        InspectEndpointPhase.validate_config("p", config)


def test_validate_config_accepts_minimal():
    InspectEndpointPhase.validate_config("p", PhaseConfig(name="p"))


# ---------------------------------------------------------------------------
# _parse_exposition
# ---------------------------------------------------------------------------


def test_parse_exposition_prometheus():
    families, fmt = _parse_exposition(PROMETHEUS_BODY, "text/plain; version=0.0.4")
    assert fmt == "prometheus"
    assert len(families) > 0


def test_parse_exposition_openmetrics():
    families, fmt = _parse_exposition(OPENMETRICS_BODY_CLEAN, "application/openmetrics-text; version=1.0.0")
    assert fmt == "openmetrics"
    assert len(families) > 0


def test_parse_exposition_empty_content_type_falls_back_to_prometheus():
    families, fmt = _parse_exposition(PROMETHEUS_BODY, "")
    assert fmt == "prometheus"
    assert len(families) > 0


def test_parse_exposition_raises_on_invalid_body():
    with pytest.raises(EndpointInspectionError, match="not valid prometheus exposition"):
        _parse_exposition("<html></html>", "text/plain")


def test_parse_exposition_raises_on_zero_families():
    with pytest.raises(EndpointInspectionError, match="zero metric families"):
        _parse_exposition("", "text/plain")


# ---------------------------------------------------------------------------
# _build_memory_text
# ---------------------------------------------------------------------------


def _result(name: str, url: str, jsonl_path, exposition_path) -> EndpointResult:
    return EndpointResult(
        name=name,
        url=url,
        status_code=200,
        content_type="text/plain; version=0.0.4",
        exposition_format="prometheus",
        metric_count=2,
        metrics_jsonl_path=str(jsonl_path),
        exposition_path=str(exposition_path),
    )


def test_build_memory_text_renders_all_fields(tmp_path):
    jsonl_path = tmp_path / "inspect_endpoint_main_metrics.jsonl"
    exposition_path = tmp_path / "inspect_endpoint_main_exposition.txt"
    text = _build_memory_text([_result("main", "http://example.test:9100/metrics", jsonl_path, exposition_path)])
    assert "main" in text
    assert "http://example.test:9100/metrics" in text
    assert "200" in text
    assert "text/plain; version=0.0.4" in text
    assert "prometheus" in text
    assert str(jsonl_path) in text
    assert str(exposition_path) in text


def test_build_memory_text_renders_every_endpoint(tmp_path):
    r1 = _result("agent", "http://host:9962/metrics", tmp_path / "a.jsonl", tmp_path / "a.txt")
    r2 = _result("operator", "http://host:9963/metrics", tmp_path / "o.jsonl", tmp_path / "o.txt")
    text = _build_memory_text([r1, r2])
    for r in (r1, r2):
        assert r.name in text
        assert r.url in text
        assert r.metrics_jsonl_path in text
        assert r.exposition_path in text


# ---------------------------------------------------------------------------
# JSONL + sidecar contract
# ---------------------------------------------------------------------------


async def test_jsonl_path_in_checkpoint(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    path_str = _endpoint_data(checkpoint)["metrics_jsonl_path"]
    assert isinstance(path_str, str)
    assert os.path.isabs(path_str)
    assert os.path.exists(path_str)


async def test_jsonl_one_row_per_family(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    rows = _read_family_rows(_jsonl_path(flow_dir))
    expected_families = list(parse_prometheus(PROMETHEUS_BODY))
    assert len(rows) == _endpoint_data(checkpoint)["metric_count"] == len(expected_families)


async def test_jsonl_row_schema(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    expected_keys = {"name", "type", "help", "unit", "label_keys", "sample_count"}
    for row in _read_family_rows(_jsonl_path(flow_dir)):
        assert set(row.keys()) == expected_keys
        assert isinstance(row["label_keys"], list)
        assert all(isinstance(k, str) for k in row["label_keys"])
        assert row["label_keys"] == sorted(row["label_keys"])
        assert len(row["label_keys"]) == len(set(row["label_keys"]))


async def test_jsonl_counter_total_stripped_prometheus(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    counter_rows = [r for r in rows if r["type"] == "counter"]
    assert len(counter_rows) == 1
    assert counter_rows[0]["name"] == "http_requests"


async def test_jsonl_counter_total_stripped_openmetrics(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(
        monkeypatch,
        _ok_handler(200, OPENMETRICS_BODY_CLEAN, "application/openmetrics-text; version=1.0.0"),
    )
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    counter_rows = [r for r in rows if r["type"] == "counter"]
    assert len(counter_rows) == 1
    assert counter_rows[0]["name"] == "http_requests"


async def test_jsonl_histogram_collapses_to_single_row(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    hist_rows = [r for r in rows if r["type"] == "histogram"]
    assert len(hist_rows) == 1
    row = hist_rows[0]
    assert row["name"] == "request_duration_seconds"
    assert "le" in row["label_keys"]


async def test_jsonl_summary_collapses_to_single_row(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(
        monkeypatch,
        _ok_handler(200, OPENMETRICS_BODY_CLEAN, "application/openmetrics-text; version=1.0.0"),
    )
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    summary_rows = [r for r in rows if r["type"] == "summary"]
    assert len(summary_rows) == 1
    row = summary_rows[0]
    assert row["name"] == "request_duration_seconds"
    assert "quantile" in row["label_keys"]


async def test_jsonl_unit_populated_for_openmetrics(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(
        monkeypatch,
        _ok_handler(200, OPENMETRICS_BODY_WITH_UNIT, "application/openmetrics-text; version=1.0.0"),
    )
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    assert len(rows) == 1
    assert rows[0]["unit"] == "seconds"


async def test_jsonl_unit_empty_for_prometheus(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    assert all(r["unit"] == "" for r in rows)


def test_jsonl_label_keys_are_union_across_samples():
    metric = Metric("multi_labels", "doc", "gauge")
    metric.samples.append(_Sample("multi_labels", {"a": "1"}, 1.0))
    metric.samples.append(_Sample("multi_labels", {"a": "1", "b": "2"}, 2.0))
    metric.samples.append(_Sample("multi_labels", {"a": "1", "c": "3"}, 3.0))

    rows = _build_jsonl_rows([metric])

    assert rows[0]["label_keys"] == ["a", "b", "c"]


async def test_jsonl_sample_count_matches_parser(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    families = list(parse_prometheus(PROMETHEUS_BODY))
    expected_counts = {m.name: len(m.samples) for m in families}
    actual_counts = {r["name"]: r["sample_count"] for r in rows}
    assert actual_counts == expected_counts


async def test_jsonl_ordering_matches_parser(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    rows = _read_family_rows(_jsonl_path(flow_dir))
    families = list(parse_prometheus(PROMETHEUS_BODY))
    assert [r["name"] for r in rows] == [m.name for m in families]


async def test_jsonl_is_deterministic_byte_for_byte(flow_dir, message_queue, monkeypatch, tmp_path_factory):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase1, _ = _make_phase(flow_dir, message_queue)
    await phase1.process_message(PhaseTrigger(id="start", phase_id=None))
    first_bytes = _jsonl_path(flow_dir).read_bytes()

    flow_dir_2 = tmp_path_factory.mktemp("second_run")
    queue_2 = asyncio.Queue()
    phase2, _ = _make_phase(flow_dir_2, queue_2)
    await phase2.process_message(PhaseTrigger(id="start", phase_id=None))
    second_bytes = _jsonl_path(flow_dir_2).read_bytes()

    assert first_bytes == second_bytes
    assert first_bytes.endswith(b"\n")


async def test_memory_text_includes_jsonl_path(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    memory = mgr.memory_content(PHASE_ID)
    assert _endpoint_data(checkpoint)["metrics_jsonl_path"] in memory


async def test_jsonl_sidecar_atomic_on_os_replace_failure(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))

    def boom(_src, _dst):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(inspect_endpoint_module.os, "replace", boom)

    phase, mgr = _make_phase(flow_dir, message_queue)

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="Failed to write metrics catalog")

    assert not _jsonl_path(flow_dir).exists()


async def test_jsonl_failure_propagates_as_phase_failure(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    blocker = flow_dir / f"{PHASE_ID}_{ENDPOINT_NAME}_metrics.jsonl.tmp"
    blocker.mkdir()

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="Failed to write metrics catalog")


# ---------------------------------------------------------------------------
# Raw exposition sidecar
# ---------------------------------------------------------------------------


async def test_exposition_path_in_checkpoint(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    path_str = _endpoint_data(checkpoint)["exposition_path"]
    assert isinstance(path_str, str)
    assert os.path.isabs(path_str)
    assert os.path.exists(path_str)


async def test_exposition_file_holds_verbatim_body(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, _mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    exposition = _exposition_path(flow_dir).read_text(encoding="utf-8")
    assert exposition == PROMETHEUS_BODY


async def test_memory_text_includes_exposition_path(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    assert _endpoint_data(checkpoint)["exposition_path"] in mgr.memory_content(PHASE_ID)


async def test_exposition_failure_propagates_as_phase_failure(flow_dir, message_queue, monkeypatch):
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue)

    # Block only the exposition temp path (the JSONL is written first and succeeds).
    blocker = flow_dir / f"{PHASE_ID}_{ENDPOINT_NAME}_exposition.txt.tmp"
    blocker.mkdir()

    await _assert_phase_fails(phase, mgr, message_queue, error_contains="Failed to write exposition snapshot")
    assert not _exposition_path(flow_dir).exists()


# ---------------------------------------------------------------------------
# Input contract — pydantic models
# ---------------------------------------------------------------------------


def test_normalize_endpoint_name_variants():
    assert normalize_endpoint_name("App Controller") == "app_controller"
    assert normalize_endpoint_name("api-server") == "api_server"
    assert normalize_endpoint_name("  Mixed_Case  ") == "mixed_case"
    assert normalize_endpoint_name("foo123") == "foo123"


def test_normalize_endpoint_name_rejects_leading_digit():
    with pytest.raises(ValueError, match="not a valid identifier"):
        normalize_endpoint_name("9metrics")


def test_endpoint_spec_rejects_url_without_scheme():
    with pytest.raises(ValidationError):
        EndpointSpec(name="main", url="example.com/metrics")


def test_inspect_input_rejects_empty_endpoints():
    with pytest.raises(ValidationError, match="at least one endpoint"):
        InspectInput(endpoints=[])


def test_inspect_input_rejects_duplicate_names():
    with pytest.raises(ValidationError, match="duplicate endpoint names"):
        InspectInput(
            endpoints=[
                EndpointSpec(name="App Controller", url="http://h:1/m"),
                EndpointSpec(name="app-controller", url="http://h:2/m"),
            ]
        )


# ---------------------------------------------------------------------------
# Multi-endpoint
# ---------------------------------------------------------------------------


def _two_endpoint_run(flow_dir, message_queue, monkeypatch):
    url_a = "http://host:9962/metrics"
    url_b = "http://host:9963/metrics"
    _install_mock_transport(
        monkeypatch,
        _multi_handler(
            {
                url_a: (200, PROMETHEUS_BODY, "text/plain"),
                url_b: (200, PROMETHEUS_BODY_SECOND, "text/plain"),
            }
        ),
    )
    phase, mgr = _make_phase(
        flow_dir,
        message_queue,
        runtime_variables=_inspect_input_var(("agent", url_a), ("operator", url_b)),
    )
    return phase, mgr, url_a, url_b


async def test_multi_endpoint_writes_one_jsonl_per_endpoint(flow_dir, message_queue, monkeypatch):
    phase, _mgr, _url_a, _url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    agent_families = {r["name"] for r in _read_family_rows(_jsonl_path(flow_dir, "agent"))}
    operator_families = {r["name"] for r in _read_family_rows(_jsonl_path(flow_dir, "operator"))}
    assert agent_families == {m.name for m in parse_prometheus(PROMETHEUS_BODY)}
    assert operator_families == {m.name for m in parse_prometheus(PROMETHEUS_BODY_SECOND)}


async def test_multi_endpoint_writes_one_exposition_per_endpoint(flow_dir, message_queue, monkeypatch):
    phase, _mgr, _url_a, _url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert _exposition_path(flow_dir, "agent").read_text(encoding="utf-8") == PROMETHEUS_BODY
    assert _exposition_path(flow_dir, "operator").read_text(encoding="utf-8") == PROMETHEUS_BODY_SECOND


async def test_jsonl_first_row_is_provenance_header(flow_dir, message_queue, monkeypatch):
    phase, _mgr, url_a, url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    for name, url in (("agent", url_a), ("operator", url_b)):
        path = _jsonl_path(flow_dir, name)
        header = _read_header(path)
        assert set(header.keys()) == {"endpoint_name", "endpoint_url", "exposition_format", "metric_families"}
        assert header["endpoint_name"] == name
        assert header["endpoint_url"] == url
        assert header["metric_families"] == len(_read_family_rows(path))


async def test_family_rows_follow_header_unchanged_schema(flow_dir, message_queue, monkeypatch):
    phase, _mgr, _url_a, _url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    expected_keys = {"name", "type", "help", "unit", "label_keys", "sample_count"}
    for name in ("agent", "operator"):
        for row in _read_family_rows(_jsonl_path(flow_dir, name)):
            assert set(row.keys()) == expected_keys


async def test_checkpoint_lists_all_endpoints(flow_dir, message_queue, monkeypatch):
    phase, mgr, url_a, url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    endpoints = checkpoint.phase_data["endpoints"]
    assert [e["name"] for e in endpoints] == ["agent", "operator"]
    assert [e["url"] for e in endpoints] == [url_a, url_b]
    expected_fields = {
        "name",
        "url",
        "status_code",
        "content_type",
        "exposition_format",
        "metric_count",
        "metrics_jsonl_path",
        "exposition_path",
    }
    for e in endpoints:
        assert set(e.keys()) == expected_fields
        assert os.path.isabs(e["metrics_jsonl_path"])
        assert os.path.exists(e["metrics_jsonl_path"])
        assert os.path.isabs(e["exposition_path"])
        assert os.path.exists(e["exposition_path"])


async def test_memory_text_includes_every_endpoint(flow_dir, message_queue, monkeypatch):
    phase, mgr, _url_a, _url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    memory = mgr.memory_content(PHASE_ID)
    for name in ("agent", "operator"):
        assert name in memory
        assert str(_jsonl_path(flow_dir, name)) in memory
        assert str(_exposition_path(flow_dir, name)) in memory


async def test_all_or_nothing_one_endpoint_fails_aborts_phase(flow_dir, message_queue, monkeypatch):
    url_a = "http://host:9962/metrics"
    url_b = "http://host:9963/metrics"
    _install_mock_transport(
        monkeypatch,
        _multi_handler(
            {
                url_a: (200, PROMETHEUS_BODY, "text/plain"),
                url_b: (503, "service unavailable", "text/plain"),
            }
        ),
    )
    phase, mgr = _make_phase(
        flow_dir,
        message_queue,
        runtime_variables=_inspect_input_var(("agent", url_a), ("operator", url_b)),
    )

    raised = await _assert_phase_fails(phase, mgr, message_queue, error_contains="[operator]")
    assert "HTTP 503" in str(raised)


async def test_multiple_failures_are_all_reported(flow_dir, message_queue, monkeypatch):
    url_a = "http://host:9962/metrics"
    url_b = "http://host:9963/metrics"
    _install_mock_transport(
        monkeypatch,
        _multi_handler(
            {
                url_a: (503, "service unavailable", "text/plain"),
                url_b: httpx.TimeoutException("slow"),
            }
        ),
    )
    phase, mgr = _make_phase(
        flow_dir,
        message_queue,
        runtime_variables=_inspect_input_var(("agent", url_a), ("operator", url_b)),
    )

    raised = await _assert_phase_fails(phase, mgr, message_queue, error_contains="2 endpoint(s) failed")
    text = str(raised)
    assert "agent" in text
    assert "operator" in text
    assert "HTTP 503" in text
    assert "timed out" in text


async def test_inspect_input_missing_raises_config_error(flow_dir, message_queue):
    phase, _mgr = _make_phase(flow_dir, message_queue, runtime_variables={})
    with pytest.raises(ConfigError, match="inspect_input"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_inspect_input_malformed_json_raises_config_error(flow_dir, message_queue):
    phase, _mgr = _make_phase(flow_dir, message_queue, runtime_variables={"inspect_input": "not json"})
    with pytest.raises(ConfigError, match="invalid 'inspect_input'"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_inspect_input_empty_endpoints_raises_config_error(flow_dir, message_queue):
    phase, _mgr = _make_phase(flow_dir, message_queue, runtime_variables={"inspect_input": '{"endpoints": []}'})
    with pytest.raises(ConfigError, match="inspect_input"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_duplicate_endpoint_names_raise_config_error(flow_dir, message_queue):
    phase, _mgr = _make_phase(
        flow_dir,
        message_queue,
        runtime_variables=_inspect_input_var(("App Controller", "http://h:1/m"), ("app-controller", "http://h:2/m")),
    )
    with pytest.raises(ConfigError, match="duplicate endpoint names"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_endpoint_name_normalized_to_snake_case(flow_dir, message_queue, monkeypatch):
    url = "http://host:9962/metrics"
    _install_mock_transport(monkeypatch, _ok_handler(200, PROMETHEUS_BODY, "text/plain"))
    phase, mgr = _make_phase(flow_dir, message_queue, runtime_variables=_inspect_input_var(("App Controller", url)))

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert _jsonl_path(flow_dir, "app_controller").exists()
    assert _exposition_path(flow_dir, "app_controller").exists()
    checkpoint = mgr.read()[PHASE_ID]
    assert _endpoint_data(checkpoint)["name"] == "app_controller"


async def test_url_without_scheme_raises_config_error(flow_dir, message_queue):
    phase, _mgr = _make_phase(
        flow_dir, message_queue, runtime_variables=_inspect_input_var(("main", "example.com/metrics"))
    )
    with pytest.raises(ConfigError, match="inspect_input"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_multi_endpoint_deterministic_jsonl(flow_dir, message_queue, monkeypatch, tmp_path_factory):
    phase1, _mgr, _url_a, _url_b = _two_endpoint_run(flow_dir, message_queue, monkeypatch)
    await phase1.process_message(PhaseTrigger(id="start", phase_id=None))
    first = {name: _jsonl_path(flow_dir, name).read_bytes() for name in ("agent", "operator")}

    flow_dir_2 = tmp_path_factory.mktemp("second_run")
    queue_2 = asyncio.Queue()
    phase2, _mgr2, _a, _b = _two_endpoint_run(flow_dir_2, queue_2, monkeypatch)
    await phase2.process_message(PhaseTrigger(id="start", phase_id=None))
    second = {name: _jsonl_path(flow_dir_2, name).read_bytes() for name in ("agent", "operator")}

    for name in ("agent", "operator"):
        assert first[name] == second[name]
        assert first[name].endswith(b"\n")
