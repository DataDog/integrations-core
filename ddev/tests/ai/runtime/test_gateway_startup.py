# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import json
from collections.abc import AsyncIterator
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Never
from unittest.mock import AsyncMock, Mock

import httpx2
import pytest
import yaml

from ddev.ai.agent.provider import AgentProvider, ModelAccessCheck
from ddev.ai.agent.registry import AgentProviderRegistry, build_agent_provider_registry
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.config.models import AgentConfig, FlowEntry, PhaseConfig, ResolvedFlow, TaskConfig
from ddev.ai.model_catalog import Route
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.runtime import gateway_auth
from ddev.ai.runtime.checkpoints import CheckpointManager, CheckpointStatus
from ddev.ai.runtime.connections import DirectConnection, GatewayConnection
from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.ai.runtime.gateway_auth import LOGIN_HELP, GatewayAuthError, GatewayTokenProducer, gateway_refresh_error
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.utils import dd_auth

from .helpers import make_success_checkpoint


def _stub_dd_auth(monkeypatch: pytest.MonkeyPatch, *, available: bool = True) -> AsyncMock:
    monkeypatch.setattr(dd_auth, "find_dd_auth", lambda: "/auth-bin/dd-auth" if available else None)
    acquire_pat = AsyncMock(return_value="ddpat_testing_secret")
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    return acquire_pat


class TrackingTransport(httpx2.MockTransport):
    closed = False

    async def aclose(self) -> None:
        self.closed = True
        await super().aclose()


def _gateway_registry(key: str | None = None, catalog: Path | None = None) -> AgentProviderRegistry:
    return build_agent_provider_registry(
        SimpleNamespace(anthropic_api_key=key, use_ai_gateway=True, models_catalog=catalog)
    )


def _agent(registry: AgentProviderRegistry, model: str) -> AgentConfig:
    return AgentConfig.model_validate({"model": model}, context={"provider_registry": registry})


@pytest.mark.parametrize("missing", [None, "binding", "key"])
async def test_missing_dd_auth_uses_direct_only_when_all_selected_models_can_run(tmp_path, monkeypatch, missing):
    models = {
        "wide": {
            "provider": "anthropic",
            "context_window": 1_000_000,
            "bindings": {
                "direct": {"protocol": "anthropic-messages", "model": "wide-direct"},
            },
        },
        "narrow": {
            "provider": "anthropic",
            "context_window": 200_000,
            "bindings": {
                "direct": {"protocol": "anthropic-messages", "model": "narrow-direct"},
                "ai-gateway": {"protocol": "anthropic-messages", "model": "anthropic/narrow-gateway"},
            },
        },
    }
    if missing == "binding":
        del models["narrow"]["bindings"]["direct"]
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(yaml.safe_dump({"models": models, "aliases": {"default": "wide"}}))
    registry = _gateway_registry(None if missing == "key" else "direct-secret", catalog)
    agents = {name: _agent(registry, name) for name in ("default", "narrow")}
    acquire_pat = _stub_dd_auth(monkeypatch, available=False)
    resources = RunResources(registry, FileAccessPolicy(tmp_path, "demo"), agents, Callbacks())
    routes = []
    try:
        if missing is None:
            assert await resources.prepare(routes.append, initial_agent=agents["default"]) is None
            (route,) = routes
            assert route.requested is Route.AI_GATEWAY
            assert route.effective is Route.DIRECT
            assert "dd-auth was not found on PATH" in route.describe()
            assert "AI Gateway access was not checked" in route.describe()
        else:
            reason = "no 'direct' binding" if missing == "binding" else "No direct credential"
            with pytest.raises(GatewayAuthError, match=rf"Direct fallback unavailable: .*{reason}"):
                await resources.prepare(routes.append, initial_agent=agents["default"])
            assert not routes
        acquire_pat.assert_not_awaited()
    finally:
        await resources.close()


async def test_gateway_startup_probes_the_adapter_for_the_initial_agent(tmp_path, monkeypatch):
    acquire_pat = _stub_dd_auth(monkeypatch)
    registry = AgentProviderRegistry(requested_route=Route.AI_GATEWAY)
    agents = {}
    bound_adapters = {}
    for name in ("provider-a", "provider-b"):
        configured = Mock(spec=AgentProvider)
        bound = Mock(spec=AgentProvider)
        configured.supported_models.return_value = bound.supported_models.return_value = frozenset({name})
        configured.for_run.return_value = bound
        registry.register(name, configured)
        agents[name] = _agent(registry, name)
        bound_adapters[name] = bound
    expected = ModelAccessCheck(200, "provider-b/binding", True)

    async def check_access(config: AgentConfig) -> ModelAccessCheck:
        acquire_pat.assert_awaited_once()
        return expected

    bound_adapters["provider-b"].check_access.side_effect = check_access
    resources = RunResources(registry, FileAccessPolicy(tmp_path, "demo"), agents, Callbacks())

    try:
        assert await resources.prepare(lambda _: None, initial_agent=agents["provider-b"]) == expected
        bound_adapters["provider-a"].check_access.assert_not_awaited()
        bound_adapters["provider-b"].check_access.assert_awaited_once_with(agents["provider-b"])
    finally:
        await resources.close()


def _orchestrator(
    tmp_path: Path,
    transport: TrackingTransport,
    monkeypatch,
    *,
    has_direct_key: bool = True,
    has_dd_auth: bool = True,
    flow: ResolvedFlow | None = None,
    resume: bool = False,
    callbacks: Callbacks | None = None,
) -> PhaseOrchestrator:
    _stub_dd_auth(monkeypatch, available=has_dd_auth)
    monkeypatch.setattr("ddev.ai.runtime.resources.GatewayConnection", partial(GatewayConnection, transport=transport))
    monkeypatch.setattr("ddev.ai.runtime.resources.DirectConnection", partial(DirectConnection, transport=transport))
    registry = _gateway_registry("direct-secret" if has_direct_key else None)
    phases = PhaseRegistry()
    phases.register("AgenticPhase", AgenticPhase)
    if flow is None:
        flow = ResolvedFlow(
            name="demo",
            agents={"writer": _agent(registry, "haiku")},
            flow=[FlowEntry(phase="run")],
            phases={"run": PhaseConfig(name="run", agent="writer", tasks=[TaskConfig(name="task", prompt="Run task")])},
            variables={},
        )
    return PhaseOrchestrator(
        resolved_flow=flow,
        phase_registry=phases,
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        provider_registry=registry,
        file_access_policy=FileAccessPolicy(tmp_path, "demo"),
        callbacks=callbacks,
        prepare_run_directory=None if resume else lambda: (tmp_path / "checkpoints.yaml").unlink(missing_ok=True),
        grace_period=0,
        resume=resume,
    )


def _message(model: str) -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _stream_message(message: dict, *, tool_call: dict | None = None) -> httpx2.Response:
    events = [("message_start", {"message": message})]
    if tool_call is None:
        events.append(("content_block_start", {"index": 0, "content_block": {"type": "text", "text": "Done"}}))
    else:
        block = {"type": "tool_use", "id": "toolu_test", "name": tool_call["name"], "input": {}}
        events.append(("content_block_start", {"index": 0, "content_block": block}))
        delta = {"type": "input_json_delta", "partial_json": json.dumps(tool_call["input"])}
        events.append(("content_block_delta", {"index": 0, "delta": delta}))
    stop_reason = "end_turn" if tool_call is None else "tool_use"
    events.extend(
        [
            ("content_block_stop", {"index": 0}),
            ("message_delta", {"delta": {"stop_reason": stop_reason}, "usage": {"output_tokens": 1}}),
            ("message_stop", {}),
        ]
    )
    stream = "".join(f"event: {name}\ndata: {json.dumps({'type': name, **data})}\n\n" for name, data in events)
    return httpx2.Response(200, text=stream, headers={"content-type": "text/event-stream"})


@pytest.mark.parametrize("has_dd_auth", [True, False], ids=["gateway", "direct-fallback"])
async def test_phase_keeps_startup_route_and_model_across_credential_refresh(tmp_path, monkeypatch, has_dd_auth):
    requests = []
    model = "claude-haiku-4-5-20251001"
    message = _message(model)
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(gateway_auth, "time", SimpleNamespace(time=lambda: clock.now))

    def handle(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        expected_model = f"anthropic/{model}" if has_dd_auth else "claude-haiku-4-5"
        stream_request = body.get("stream", False)
        expected_token = "direct-secret"
        if has_dd_auth:
            expected_token = "ddpat_refreshed" if stream_request else "ddpat_testing_secret"
        assert body["model"] == expected_model
        assert request.headers["authorization"] == f"Bearer {expected_token}"
        requests.append(stream_request)
        if not stream_request:
            clock.now += gateway_auth.TOKEN_USE_WINDOW
            return httpx2.Response(200, json=message)

        return _stream_message(message)

    transport = TrackingTransport(handle)
    orchestrator = _orchestrator(
        tmp_path, transport, monkeypatch, has_direct_key=not has_dd_auth, has_dd_auth=has_dd_auth
    )
    acquire_pat = AsyncMock(side_effect=["ddpat_testing_secret", "ddpat_refreshed"])
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    await orchestrator.run_async()

    if has_dd_auth:
        assert requests[0] is False
        requests = requests[1:]
    assert requests and all(requests)
    assert acquire_pat.await_count == (2 if has_dd_auth else 0)
    assert CheckpointManager(tmp_path / "checkpoints.yaml").read()["run"].status is CheckpointStatus.SUCCESS
    assert transport.closed


@pytest.mark.parametrize(
    ("denial", "expected_error", "expected_message"),
    [
        ("refresh", CredentialRefreshError, "could not be refreshed"),
        ("http-403", GatewayAuthError, r"denied access \(HTTP 403\)"),
    ],
)
async def test_subagent_gateway_denial_ends_run_and_keeps_completed_phase_checkpoint(
    tmp_path, monkeypatch, caplog, denial, expected_error, expected_message
):
    registry = _gateway_registry()
    tool_name = "spawn_identical_subagents"
    writer = _agent(registry, "haiku").model_copy(update={"tools": [tool_name]})
    flow = ResolvedFlow(
        name="demo",
        agents={"writer": writer},
        flow=[FlowEntry(phase="plan"), FlowEntry(phase="write", dependencies=["plan"])],
        phases={
            name: PhaseConfig(name=name, agent="writer", tasks=[TaskConfig(name=name, prompt=name)])
            for name in ("plan", "write")
        },
        variables={},
    )
    checkpoints = CheckpointManager(tmp_path / "checkpoints.yaml")
    completed_checkpoint = None
    subagent_running = False
    callback_set = CallbackSet()

    @callback_set.on_agent_start
    async def mark_subagent(scope: AgentScope, _prompt: str, _tools: list[str]) -> None:
        nonlocal subagent_running
        subagent_running = scope.role is AgentRole.SUBAGENT

    async def token_for(provider: str) -> str:
        if denial == "refresh" and subagent_running:
            raise gateway_refresh_error(RefreshFailureCause.LOGIN_TIMED_OUT)
        return "ddpat_testing_secret"

    producer = Mock(spec=GatewayTokenProducer, available=True)
    producer.token_for.side_effect = token_for
    monkeypatch.setattr("ddev.ai.runtime.resources.GatewayTokenProducer", lambda: producer)
    message = _message("claude-haiku-4-5-20251001")

    def handle(request: httpx2.Request) -> httpx2.Response:
        nonlocal completed_checkpoint
        if not json.loads(request.content).get("stream"):
            return httpx2.Response(200, json=message)
        if completed_checkpoint is None and (completed_checkpoint := checkpoints.read().get("plan")) is not None:
            return _stream_message(
                message,
                tool_call={
                    "name": tool_name,
                    "input": {
                        "system_prompt": "Help the writer",
                        "assignments": [{"name": "review", "prompt": "Review the plan"}],
                    },
                },
            )
        if denial == "http-403" and subagent_running:
            return httpx2.Response(403, text="ddpat_testing_secret")
        return _stream_message(message)

    orchestrator = _orchestrator(
        tmp_path, TrackingTransport(handle), monkeypatch, flow=flow, callbacks=Callbacks([callback_set])
    )
    with pytest.raises(expected_error, match=expected_message) as caught:
        await orchestrator.run_async()

    assert str(caught.value) in caplog.text
    assert "ddpat_testing_secret" not in str(caught.value) + caplog.text
    assert checkpoints.successful_phases() == {"plan"}
    assert checkpoints.read()["plan"] == completed_checkpoint


@pytest.mark.parametrize("status", [401, 403])
async def test_gateway_denial_stops_startup_and_does_not_expose_tokens(tmp_path, monkeypatch, caplog, status):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    checkpoint = run_dir / "checkpoints.yaml"
    checkpoint.write_text("previous run")
    handle = AsyncMock(return_value=httpx2.Response(status, text="ddpat_testing_secret"))
    transport = TrackingTransport(handle)
    orchestrator = _orchestrator(run_dir, transport, monkeypatch)
    message = "returned the same unusable credential" if status == 401 else r"denied access \(HTTP 403\)"
    with pytest.raises(FatalProcessingError, match=message) as caught:
        await orchestrator.run_async()

    assert "ddpat_testing_secret" not in str(caught.value) + caplog.text
    if status == 401:
        assert "dd-auth --no-cache" in str(caught.value)
    assert list(run_dir.iterdir()) == [checkpoint]
    assert checkpoint.read_text() == "previous run"
    handle.assert_awaited_once()
    assert transport.closed


@pytest.mark.parametrize(
    ("network_error", "message"),
    [
        (httpx2.ConnectError, "AI Gateway startup connection failed."),
        (httpx2.ReadTimeout, "AI Gateway startup check timed out."),
    ],
)
async def test_gateway_startup_reports_network_failure_without_transport_details(
    tmp_path, monkeypatch, network_error, message
):
    handle = AsyncMock(side_effect=network_error("private transport detail"))
    orchestrator = _orchestrator(tmp_path, TrackingTransport(handle), monkeypatch)

    with pytest.raises(FatalProcessingError) as caught:
        await orchestrator.run_async()

    assert f"{message} Retry the run. {LOGIN_HELP}" in str(caught.value)
    assert "private transport detail" not in str(caught.value)
    handle.assert_awaited_once()


@pytest.mark.parametrize("resume", [False, True], ids=["fresh", "resume"])
async def test_gateway_probes_first_pending_agent_in_dependency_order(tmp_path, monkeypatch, resume):
    registry = _gateway_registry()
    agents = {"writer": _agent(registry, "sonnet"), "reader": _agent(registry, "haiku")}
    flow = ResolvedFlow(
        name="demo",
        agents=dict(reversed(agents.items())) if resume else agents,
        flow=[FlowEntry(phase="read"), FlowEntry(phase="write", dependencies=["read"])],
        phases={
            "write": PhaseConfig(name="write", agent="writer", tasks=[TaskConfig(name="write", prompt="Write")]),
            "read": PhaseConfig(name="read", agent="reader", tasks=[TaskConfig(name="read", prompt="Read")]),
        },
        variables={},
    )
    checkpoint = tmp_path / "checkpoints.yaml"
    CheckpointManager(checkpoint).write_phase_checkpoint("read", make_success_checkpoint())
    previous_state = checkpoint.read_text()
    denied_model = "claude-sonnet-5" if resume else "claude-haiku-4-5-20251001"
    requested_models = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        binding = json.loads(request.content)["model"]
        requested_models.append(binding)
        _, _, model = binding.partition("/")
        if model == denied_model:
            return httpx2.Response(403)
        return httpx2.Response(200, json=_message(model))

    orchestrator = _orchestrator(tmp_path, TrackingTransport(handle), monkeypatch, flow=flow, resume=resume)
    with pytest.raises(FatalProcessingError, match=r"denied access \(HTTP 403\)"):
        await orchestrator.run_async()

    assert requested_models == [f"anthropic/{denied_model}"]
    assert checkpoint.read_text() == previous_state


@pytest.mark.parametrize("cancel_at", ["acquisition", "probe", "refresh"])
async def test_gateway_startup_cancellation_leaves_run_state_untouched(tmp_path, monkeypatch, cancel_at):
    started = asyncio.Event()

    async def wait_until_cancelled(_: object, *, rejected_pat: str | None = None) -> Never:
        started.set()
        await asyncio.Future()
        raise AssertionError("Startup should have been cancelled")

    checkpoint = tmp_path / "checkpoints.yaml"
    checkpoint.write_text("previous run")
    handle = AsyncMock(side_effect=wait_until_cancelled)
    transport = TrackingTransport(handle)
    orchestrator = _orchestrator(tmp_path, transport, monkeypatch)
    if cancel_at == "acquisition":
        monkeypatch.setattr(dd_auth, "acquire_datadog_pat", wait_until_cancelled)
    elif cancel_at == "refresh":
        handle.side_effect = None
        handle.return_value = httpx2.Response(401)

        async def acquire_pat(_: str, *, rejected_pat: str | None) -> str:
            if not handle.await_count:
                return "ddpat_old"
            return await wait_until_cancelled(None)

        monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    run = asyncio.create_task(orchestrator.run_async())
    async with asyncio.timeout(1):
        await started.wait()
        run.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run

    assert checkpoint.read_text() == "previous run"
    if cancel_at == "acquisition":
        handle.assert_not_awaited()
    else:
        assert transport.closed


async def test_gateway_stream_failure_closes_connection_without_replaying_generation(tmp_path, monkeypatch):
    model = "claude-haiku-4-5-20251001"
    message = _message(model)
    requests = []

    class InterruptedStream(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            event = {"type": "message_start", "message": message}
            yield f"event: message_start\ndata: {json.dumps(event)}\n\n".encode()
            raise httpx2.ReadError("connection interrupted")

    def handle(request: httpx2.Request) -> httpx2.Response:
        stream = json.loads(request.content).get("stream", False)
        requests.append(stream)
        if stream:
            return httpx2.Response(200, stream=InterruptedStream(), headers={"content-type": "text/event-stream"})
        return httpx2.Response(200, json=message)

    transport = TrackingTransport(handle)
    orchestrator = _orchestrator(tmp_path, transport, monkeypatch)
    with pytest.raises(httpx2.ReadError, match="connection interrupted"):
        await orchestrator.run_async()

    assert requests == [False, True]
    assert transport.closed
