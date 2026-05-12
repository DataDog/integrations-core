# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

import httpx
import pytest
from prometheus_client import Metric
from prometheus_client.parser import text_string_to_metric_families as parse_prometheus

from ddev.ai.flows.openmetrics.phases import validate_endpoint as validate_endpoint_module
from ddev.ai.flows.openmetrics.phases.validate_endpoint import (
    EndpointValidationError,
    ValidateEndpointPhase,
    _build_memory_text,
    _parse_exposition,
)
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.event_bus.exceptions import MessageProcessingError

ENDPOINT_URL = "http://example.test:9100/metrics"

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flow_dir(tmp_path):
    return tmp_path


@pytest.fixture
def message_queue():
    return asyncio.Queue()


def _make_phase(
    flow_dir,
    message_queue,
    *,
    phase_id: str = "validate_endpoint",
    runtime_variables: dict[str, str] | None = None,
) -> tuple[ValidateEndpointPhase, CheckpointManager]:
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    phase = ValidateEndpointPhase(
        phase_id=phase_id,
        dependencies=[],
        config=PhaseConfig(),
        checkpoint_manager=checkpoint_manager,
        runtime_variables=runtime_variables if runtime_variables is not None else {"endpoint_url": ENDPOINT_URL},
        flow_variables={},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


def _install_mock_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient inside the phase module to use a MockTransport handler."""
    real_client_cls = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(validate_endpoint_module.httpx, "AsyncClient", factory)


def _ok_handler(status: int, body: str, content_type: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, content=body.encode("utf-8"), headers={"Content-Type": content_type})

    return handler


def _raising_handler(exc: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


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
    expected_names = [m.name for m in expected_families[:10]]

    memory = mgr.memory_content("validate_endpoint")
    assert ENDPOINT_URL in memory
    assert "HTTP status:** 200" in memory
    assert expected_names[0] in memory
    assert expected_families[0].type in memory

    checkpoint = mgr.read()["validate_endpoint"]
    assert checkpoint["status"] == "success"
    assert checkpoint["exposition_format"] == "prometheus"
    assert checkpoint["metric_count"] == len(expected_families)
    assert checkpoint["sample_metric_names"] == expected_names
    assert checkpoint["status_code"] == 200
    assert checkpoint["endpoint_url"] == ENDPOINT_URL
    assert checkpoint["tokens"] == {"total_input": 0, "total_output": 0}


async def test_success_with_openmetrics_body(flow_dir, message_queue, monkeypatch):
    content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
    _install_mock_transport(monkeypatch, _ok_handler(200, OPENMETRICS_BODY, content_type))
    phase, mgr = _make_phase(flow_dir, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()["validate_endpoint"]
    assert checkpoint["status"] == "success"
    assert checkpoint["exposition_format"] == "openmetrics"
    assert checkpoint["content_type"] == content_type
    assert checkpoint["metric_count"] >= 1


# ---------------------------------------------------------------------------
# Phase failure paths
# ---------------------------------------------------------------------------


async def _assert_phase_fails(phase, mgr, message_queue, *, error_contains: str):
    """Run execute, expect failure, drive on_error like the framework would."""
    trigger = PhaseTrigger(id="start", phase_id=None)
    context = {
        "endpoint_url": phase._runtime_variables.get("endpoint_url"),
        "phase_name": phase._phase_id,
    }
    try:
        await phase.execute(context)
    except Exception as raised:
        wrapped = MessageProcessingError(phase._phase_id, trigger, raised)
        await phase.on_error(wrapped)
        checkpoint = mgr.read()[phase._phase_id]
        assert checkpoint["status"] == "failed"
        assert error_contains.lower() in checkpoint["error"].lower()
        msg = message_queue.get_nowait()
        assert isinstance(msg, PhaseFailedMessage)
        assert error_contains.lower() in msg.error.lower()
        return raised
    pytest.fail(f"Expected execute() to raise; error should contain {error_contains!r}")


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


async def test_failure_missing_endpoint_url(flow_dir, message_queue):
    phase, mgr = _make_phase(flow_dir, message_queue, runtime_variables={})

    trigger = PhaseTrigger(id="start", phase_id=None)
    with pytest.raises(FlowConfigError, match="endpoint_url"):
        await phase.process_message(trigger)

    wrapped = MessageProcessingError(phase._phase_id, trigger, FlowConfigError("endpoint_url required"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["validate_endpoint"]
    assert checkpoint["status"] == "failed"
    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def test_validate_config_rejects_agent():
    with pytest.raises(FlowConfigError, match="must not declare 'agent'"):
        ValidateEndpointPhase.validate_config("p", PhaseConfig(agent="x"), {"x": AgentConfig()})


def test_validate_config_rejects_tasks():
    config = PhaseConfig(tasks=[TaskConfig(name="t", prompt="hi")])
    with pytest.raises(FlowConfigError, match="must not declare 'tasks'"):
        ValidateEndpointPhase.validate_config("p", config, {})


def test_validate_config_rejects_checkpoint():
    config = PhaseConfig(checkpoint=CheckpointConfig(memory_prompt="x"))
    with pytest.raises(FlowConfigError, match="must not declare 'checkpoint'"):
        ValidateEndpointPhase.validate_config("p", config, {})


def test_validate_config_accepts_minimal():
    ValidateEndpointPhase.validate_config("p", PhaseConfig(), {})


# ---------------------------------------------------------------------------
# _parse_exposition
# ---------------------------------------------------------------------------


def test_parse_exposition_prometheus():
    families, fmt = _parse_exposition(PROMETHEUS_BODY, "text/plain; version=0.0.4")
    assert fmt == "prometheus"
    assert len(families) > 0


def test_parse_exposition_openmetrics():
    families, fmt = _parse_exposition(OPENMETRICS_BODY, "application/openmetrics-text; version=1.0.0")
    assert fmt == "openmetrics"
    assert len(families) > 0


def test_parse_exposition_empty_content_type_falls_back_to_prometheus():
    families, fmt = _parse_exposition(PROMETHEUS_BODY, "")
    assert fmt == "prometheus"
    assert len(families) > 0


def test_parse_exposition_raises_on_invalid_body():
    with pytest.raises(EndpointValidationError, match="not valid prometheus exposition"):
        _parse_exposition("<html></html>", "text/plain")


def test_parse_exposition_raises_on_zero_families():
    with pytest.raises(EndpointValidationError, match="zero metric families"):
        _parse_exposition("", "text/plain")


# ---------------------------------------------------------------------------
# _build_memory_text
# ---------------------------------------------------------------------------


def test_build_memory_text_renders_all_fields():
    families = [
        Metric("widgets", "Widget count.", "counter"),
        Metric("gizmos", "Gizmo gauge.", "gauge"),
    ]
    text = _build_memory_text(
        url="http://example.test:9100/metrics",
        status=200,
        content_type="text/plain; version=0.0.4",
        exposition_format="prometheus",
        families=families,
    )
    assert "http://example.test:9100/metrics" in text
    assert "200" in text
    assert "text/plain; version=0.0.4" in text
    assert "prometheus" in text
    assert "widgets" in text
    assert "counter" in text
    assert "gizmos" in text
    assert "gauge" in text
