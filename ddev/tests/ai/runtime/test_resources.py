# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.runtime.resources import HTTP_RESPONSES_DIR_NAME, RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.http.base import FetchedResponse, HttpRequestInput, HttpRequestTool
from tests.ai.config.utils import make_agent_config


def make_resources(tmp_path: Path, run_root: Path) -> RunResources:
    provider = MagicMock()
    provider.build_agent.return_value = MagicMock()
    registry = AgentProviderRegistry()
    registry.register("test", provider)
    return RunResources(
        provider_registry=registry,
        file_access_policy=FileAccessPolicy(write_root=tmp_path, integration_name="sample"),
        agents={},
        callbacks=Callbacks(),
        run_root=run_root,
    )


def build_runtime(resources: RunResources, owner_id: str, tools: list[str]) -> AgentRuntime:
    return resources.agent_runtime_factory.build_runtime(
        agent_config=make_agent_config(provider="test", tools=tools),
        system_prompt="system",
        process_factory=resources.process_factory,
        scope=AgentScope(owner_id=owner_id, role=AgentRole.PHASE, phase_id=owner_id),
    )


async def test_http_artifacts_are_shared_across_agent_runtimes_and_preserved_on_resume(tmp_path: Path, monkeypatch):
    async def fake_fetch(
        self: HttpRequestTool,
        tool_input: HttpRequestInput,
        *,
        method: str,
        json_body: object,
    ) -> FetchedResponse:
        body = json.dumps({"method": method, "body": json_body}).encode()
        return FetchedResponse(
            url=httpx.URL(tool_input.url),
            status=200,
            content_type="application/json",
            location=None,
            body=body,
            charset="utf-8",
            complete=True,
            fetched_at=datetime.now(UTC),
        )

    monkeypatch.setattr(HttpRequestTool, "_fetch", fake_fetch)
    run_root = tmp_path / "run"
    first_launch = make_resources(tmp_path, run_root)
    get_runtime = build_runtime(first_launch, "design", ["http_get"])
    post_runtime = build_runtime(first_launch, "build", ["http_post", "read_file"])

    get_result = await get_runtime.tool_registry.run(
        "http_get", {"url": "http://localhost:4200/api/openapi.json", "save_response": True}
    )
    post_result = await post_runtime.tool_registry.run(
        "http_post", {"url": "http://localhost:4200/api/task_runs/filter", "json": {}, "save_response": True}
    )

    assert get_result.success and post_result.success
    get_path = Path(json.loads(get_result.data)["saved_to"])
    post_path = Path(json.loads(post_result.data)["saved_to"])
    assert get_path.parent == post_path.parent
    assert get_path.parent.parent == run_root / HTTP_RESPONSES_DIR_NAME
    assert get_path != post_path
    assert json.loads(get_path.read_text())["method"] == "GET"
    assert json.loads(post_path.read_text())["method"] == "POST"
    assert (await post_runtime.tool_registry.run("read_file", {"path": str(get_path)})).success

    resumed = make_resources(tmp_path, run_root)
    resumed_runtime = build_runtime(resumed, "review", ["http_get"])
    resumed_result = await resumed_runtime.tool_registry.run(
        "http_get", {"url": "http://localhost:4200/api/health", "save_response": True}
    )

    assert resumed_result.success
    resumed_path = Path(json.loads(resumed_result.data)["saved_to"])
    assert resumed_path.parent != get_path.parent
    assert get_path.exists() and post_path.exists() and resumed_path.exists()
