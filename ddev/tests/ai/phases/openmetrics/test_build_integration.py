# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.types import AgentResponse, ToolResultMessage
from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseTrigger
from ddev.ai.phases.openmetrics.build_integration import OpenMetricsBuildPhase
from ddev.ai.phases.openmetrics.label_hygiene import LabelHygieneError
from ddev.ai.runtime.checkpoints import (
    CheckpointTokenInfo,
    SuccessCheckpoint,
    TaskValidationRecord,
)
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.phases.helpers import MockAgent, make_agent_phase, make_goal_verdict, make_response


def make_config() -> PhaseConfig:
    return PhaseConfig(
        name="build_integration",
        agent="writer",
        tasks=[TaskConfig(name="write_code", prompt="Write code.", goal="Verify code.", max_validation_attempts=3)],
    )


@pytest.mark.parametrize(
    ("task_names", "match"),
    [([], "at least one task"), (["other"], "task named 'write_code'"), (["write_code", "write_code"], "exactly one")],
)
def test_requires_exactly_one_write_code_task(task_names: list[str], match: str) -> None:
    config = PhaseConfig(
        name="build_integration",
        agent="writer",
        tasks=[TaskConfig(name=name, prompt="x") for name in task_names],
    )

    with pytest.raises(ConfigError, match=match):
        OpenMetricsBuildPhase.validate_config("build_integration", config)


async def test_repairs_label_hygiene_before_single_model_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    catalog.write_text(
        json.dumps({"endpoint_name": "api"})
        + "\n"
        + json.dumps({"name": "iris_system_info", "label_keys": ["host", "version"]})
        + "\n",
        encoding="utf-8",
    )
    check_path = tmp_path / "iris" / "datadog_checks" / "iris" / "check.py"
    check_path.parent.mkdir(parents=True)
    check_path.write_text(
        "class IrisCheck:\n"
        "    def get_default_config(self):\n"
        "        return {'rename_labels': {'host': 'iris_host'}}\n",
        encoding="utf-8",
    )

    class RepairingAgent(MockAgent):
        async def send(
            self,
            content: str | list[ToolResultMessage],
            allowed_tools: list[str] | None = None,
        ) -> AgentResponse:
            if len(self.send_calls) == 1:
                check_path.write_text(
                    "class IrisCheck:\n"
                    "    def get_default_config(self):\n"
                    "        return {'rename_labels': {'host': 'iris_host', 'version': 'iris_version'}}\n",
                    encoding="utf-8",
                )
            return await super().send(content, allowed_tools)

    worker = RepairingAgent(
        [
            make_response("initial implementation", 10, 5),
            make_response("fixed version", 8, 4),
            make_response("phase memory", 2, 1),
        ]
    )
    reviewer = MockAgent([make_response(make_goal_verdict(True), 6, 3)])

    def goal_runtime_builder(_owner_id: str) -> AgentRuntime:
        return AgentRuntime(agent=reviewer, tool_registry=ToolRegistry([]))

    phase, checkpoint_manager = make_agent_phase(
        tmp_path,
        worker,
        monkeypatch,
        message_queue,
        phase_id="build_integration",
        dependencies=["inspect_endpoint"],
        tasks=make_config().tasks,
        runtime_variables={"integration": "Iris"},
        goal_runtime_builder=goal_runtime_builder,
        phase_cls=OpenMetricsBuildPhase,
        phase_kwargs={"write_root": tmp_path},
    )
    checkpoint_manager.write_phase_checkpoint(
        "inspect_endpoint",
        success_checkpoint(tmp_path, [{"metrics_jsonl_path": str(catalog)}]),
    )

    checks = phase.deterministic_checks(make_config().tasks[0], {"integration": "Iris"})
    assert [check.name for check in checks] == ["label hygiene"]

    await phase.process_message(PhaseTrigger(id="inspect-finished", phase_id="inspect_endpoint"))

    checkpoint = checkpoint_manager.read()["build_integration"]
    assert checkpoint.task_validations == [TaskValidationRecord(task="write_code", attempts=2, final_valid=True)]
    assert len(reviewer.send_calls) == 1
    repair_prompt = worker.send_calls[1]
    assert isinstance(repair_prompt, str)
    assert "Deterministic checks failed" in repair_prompt
    assert "## label hygiene" in repair_prompt
    assert "`version` (reserved) is not renamed or excluded" in repair_prompt
    assert "`iris_system_info`" in repair_prompt


def success_checkpoint(tmp_path: Path, endpoints: object) -> SuccessCheckpoint:
    return SuccessCheckpoint(
        started_at="2026-08-05T00:00:00+00:00",
        finished_at="2026-08-05T00:00:01+00:00",
        tokens=CheckpointTokenInfo(total_input=0, total_output=0),
        memory_path=str(tmp_path / "inspect_endpoint_memory.md"),
        phase_data={"endpoints": endpoints},
    )


def make_build_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> OpenMetricsBuildPhase:
    phase, _ = make_agent_phase(
        tmp_path,
        MockAgent([]),
        monkeypatch,
        message_queue,
        phase_id="build_integration",
        tasks=make_config().tasks,
        runtime_variables={"integration": "Iris"},
        phase_cls=OpenMetricsBuildPhase,
        phase_kwargs={"write_root": tmp_path},
    )
    return cast(OpenMetricsBuildPhase, phase)


@pytest.mark.parametrize("integration", [None, 123, "!!!"])
def test_invalid_integration_aborts_label_hygiene_check(
    integration: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    phase = make_build_phase(tmp_path, monkeypatch, message_queue)

    with pytest.raises(ConfigError, match="integration"):
        phase._check_label_hygiene({"integration": integration})


@pytest.mark.parametrize(
    ("context", "match"),
    [
        ({}, "does not contain checkpoints"),
        ({"checkpoints": {}}, "Successful 'inspect_endpoint' checkpoint is required"),
    ],
)
def test_invalid_checkpoint_context_aborts_label_hygiene_check(
    context: dict[str, object],
    match: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    phase = make_build_phase(tmp_path, monkeypatch, message_queue)

    with pytest.raises(LabelHygieneError, match=match):
        phase._catalog_paths(context)


@pytest.mark.parametrize(
    ("endpoints", "match"),
    [([], "no endpoint catalogs"), ([{}], "invalid endpoint catalog entry")],
)
def test_invalid_endpoint_catalogs_abort_label_hygiene_check(
    endpoints: object,
    match: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    phase = make_build_phase(tmp_path, monkeypatch, message_queue)
    context = {"checkpoints": {"inspect_endpoint": success_checkpoint(tmp_path, endpoints)}}

    with pytest.raises(LabelHygieneError, match=match):
        phase._catalog_paths(context)


def test_misnamed_generated_check_aborts_instead_of_retrying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    catalog = tmp_path / "metrics.jsonl"
    catalog.write_text(json.dumps({"name": "metric", "label_keys": ["host"]}), encoding="utf-8")
    misplaced = tmp_path / "iris_db_" / "datadog_checks" / "iris_db_" / "check.py"
    misplaced.parent.mkdir(parents=True)
    misplaced.write_text("", encoding="utf-8")
    phase = make_build_phase(tmp_path, monkeypatch, message_queue)
    context = {
        "integration": "Iris DB!",
        "checkpoints": {"inspect_endpoint": success_checkpoint(tmp_path, [{"metrics_jsonl_path": str(catalog)}])},
    }

    with pytest.raises(LabelHygieneError, match="scaffolded integration name does not match"):
        phase._check_label_hygiene(context)


def test_missing_generated_check_is_repairable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message_queue: asyncio.Queue,
) -> None:
    catalog = tmp_path / "metrics.jsonl"
    catalog.write_text(json.dumps({"name": "metric", "label_keys": ["host"]}), encoding="utf-8")
    phase = make_build_phase(tmp_path, monkeypatch, message_queue)
    context = {
        "integration": "Iris",
        "checkpoints": {"inspect_endpoint": success_checkpoint(tmp_path, [{"metrics_jsonl_path": str(catalog)}])},
    }

    reason = phase._check_label_hygiene(context)

    assert reason is not None
    assert "does not exist at the expected path" in reason
