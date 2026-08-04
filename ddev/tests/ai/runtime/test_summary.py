# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ddev.ai.agent.scope import AgentRole
from ddev.ai.agent.types import StopReason
from ddev.ai.config.models import FlowEntry, ResolvedFlow
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.outcome import (
    FailureKind,
    PhaseReport,
    PhaseReportStatus,
    RunOutcome,
    RunSummaryMetadata,
    RunSummaryStatus,
    RunVerdict,
)
from ddev.ai.runtime.summary import (
    RUN_SUMMARY_MAX_TOKENS,
    RUN_SUMMARY_SYSTEM_PROMPT,
    RUN_SUMMARY_TOOLS,
    TRUNCATION_MARKER,
    RunSummarizer,
    RunSummaryBudget,
)

from .helpers import make_success_checkpoint


def make_flow() -> ResolvedFlow:
    return ResolvedFlow(
        name="demo",
        description="Build the demo output",
        agents={},
        phases={},
        flow=[FlowEntry(phase="inspect")],
        variables={"api_key": "SECRET-RUNTIME-VALUE"},
    )


def make_outcome(tmp_path: Path) -> RunOutcome:
    return RunOutcome(
        flow_name="demo",
        verdict=RunVerdict.SUCCEEDED,
        failure_kind=FailureKind.NONE,
        failed_phase=None,
        error=None,
        error_type=None,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:10+00:00",
        duration_seconds=10,
        phases=[
            PhaseReport(
                phase_id="inspect",
                status=PhaseReportStatus.SUCCEEDED,
                started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:10+00:00",
                duration_seconds=10,
                input_tokens=10,
                output_tokens=5,
                goal_validations=None,
                error=None,
                error_type=None,
            )
        ],
        recorded_input_tokens=10,
        recorded_output_tokens=5,
        resumed=False,
        skipped_on_resume=[],
        run_dir=str(tmp_path),
        summary=RunSummaryMetadata(status=RunSummaryStatus.GENERATING),
    )


class FakeProcessFactory:
    def __init__(self, process: Any) -> None:
        self.process = process
        self.scope = None

    def create(self, *, scope: Any, agent_config: Any, system_prompt: str) -> Any:
        self.scope = scope
        return self.process


class FakeResources:
    def __init__(self, process: Any, tmp_path: Path) -> None:
        self.repository_root = str(tmp_path.parent)
        self.process_factory = FakeProcessFactory(process)
        self.agent_values: dict[str, Any] | None = None

    def validate_agent_config(self, values: dict[str, Any]) -> Any:
        self.agent_values = values
        return SimpleNamespace(**values)


class SuccessfulProcess:
    async def start(self, prompt: str) -> Any:
        return SimpleNamespace(
            final_response=SimpleNamespace(
                text="# Run summary\n\nCompleted the demo.",
                stop_reason=StopReason.END_TURN,
            ),
            total_input_tokens=21,
            total_output_tokens=8,
        )


def build_summarizer(
    tmp_path: Path,
    process: Any,
    *,
    runtime_variables: dict[str, Any] | None = None,
    resolved_flow: ResolvedFlow | None = None,
) -> tuple[RunSummarizer, CheckpointManager, FakeResources]:
    manager = CheckpointManager(tmp_path / "checkpoints.yaml")
    manager.write_phase_checkpoint("inspect", make_success_checkpoint(memory_path=str(manager.memory_path("inspect"))))
    resources = FakeResources(process, tmp_path)
    summarizer = RunSummarizer(
        resolved_flow=resolved_flow if resolved_flow is not None else make_flow(),
        checkpoint_manager=manager,
        resources=resources,  # type: ignore[arg-type]
        runtime_variables=runtime_variables if runtime_variables is not None else {"prd": "Required product behavior."},
    )
    return summarizer, manager, resources


def test_prompt_is_bounded_includes_prd_and_excludes_other_flow_variables(tmp_path: Path) -> None:
    summarizer, manager, _ = build_summarizer(tmp_path, SuccessfulProcess())
    manager.write_memory("inspect", "x" * (RunSummaryBudget.PHASE_SOURCE + 100))

    prompt = summarizer.build_prompt(make_outcome(tmp_path))

    assert len(prompt) <= RunSummaryBudget.PROMPT
    assert TRUNCATION_MARKER in prompt
    assert "SECRET-RUNTIME-VALUE" not in prompt
    assert "## Product requirements document" in prompt
    assert "Required product behavior." in prompt
    assert "Authoritative status: succeeded" in prompt


def test_missing_prd_is_labelled_not_provided(tmp_path: Path) -> None:
    summarizer, _, _ = build_summarizer(tmp_path, SuccessfulProcess(), runtime_variables={})

    prompt = summarizer.build_prompt(make_outcome(tmp_path))

    assert "<PRD NOT PROVIDED>" in prompt


def test_system_prompt_requires_log_fallback_for_incomplete_memory() -> None:
    normalized_prompt = " ".join(RUN_SUMMARY_SYSTEM_PROMPT.split())
    assert "inspect that phase's role-partitioned JSONL log" in normalized_prompt
    assert "max_tokens stop reason" in normalized_prompt


def test_missing_memory_is_labelled_unavailable(tmp_path: Path) -> None:
    summarizer, _, _ = build_summarizer(tmp_path, SuccessfulProcess())

    prompt = summarizer.build_prompt(make_outcome(tmp_path))

    assert "<PHASE MEMORY UNAVAILABLE>" in prompt
    assert "not evidence that no work happened" in prompt


def test_unreadable_memory_is_labelled_without_aborting_prompt(tmp_path: Path) -> None:
    summarizer, manager, _ = build_summarizer(tmp_path, SuccessfulProcess())
    manager.memory_path("inspect").write_bytes(b"\xff")

    prompt = summarizer.build_prompt(make_outcome(tmp_path))

    assert "<PHASE MEMORY UNREADABLE:" in prompt
    assert "Authoritative status: succeeded" in prompt


def test_unreadable_checkpoints_are_labelled_without_aborting_prompt(tmp_path: Path) -> None:
    summarizer, manager, _ = build_summarizer(tmp_path, SuccessfulProcess())
    manager.checkpoints_path.write_bytes(b"\xff")

    prompt = summarizer.build_prompt(make_outcome(tmp_path))

    assert "<CHECKPOINTS UNREADABLE:" in prompt
    assert "Authoritative status: succeeded" in prompt


def test_stale_checkpoint_and_memory_do_not_override_not_run_status(tmp_path: Path) -> None:
    summarizer, manager, _ = build_summarizer(tmp_path, SuccessfulProcess())
    manager.write_memory("inspect", "STALE MEMORY CLAIMING SUCCESS")
    outcome = make_outcome(tmp_path)
    not_run_report = outcome.phases[0].model_copy(
        update={
            "status": PhaseReportStatus.NOT_RUN,
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
        }
    )
    outcome = outcome.model_copy(update={"phases": [not_run_report]})

    prompt = summarizer.build_prompt(outcome)

    assert "Authoritative status: not_run" in prompt
    assert "CHECKPOINT UNAVAILABLE OR INCONSISTENT" in prompt
    assert "STALE MEMORY CLAIMING SUCCESS" not in prompt


def test_large_flow_keeps_every_phase_label_within_total_budget(tmp_path: Path) -> None:
    entries = [FlowEntry(phase=f"phase_{index}") for index in range(200)]
    large_flow = ResolvedFlow(
        name="large",
        agents={},
        phases={},
        flow=entries,
        variables={},
    )
    summarizer, _, _ = build_summarizer(tmp_path, SuccessfulProcess(), resolved_flow=large_flow)
    base_report = make_outcome(tmp_path).phases[0]
    reports = [
        base_report.model_copy(update={"phase_id": entry.phase, "status": PhaseReportStatus.NOT_RUN})
        for entry in entries
    ]
    outcome = make_outcome(tmp_path).model_copy(update={"flow_name": "large", "phases": reports})

    prompt = summarizer.build_prompt(outcome)

    assert len(prompt) <= RunSummaryBudget.PROMPT
    assert all(f"### Phase: {entry.phase}" in prompt for entry in entries)


async def test_success_persists_markdown_and_records_read_only_scope(tmp_path: Path) -> None:
    summarizer, manager, resources = build_summarizer(tmp_path, SuccessfulProcess())

    attempt = await summarizer.summarize(make_outcome(tmp_path))

    assert attempt.metadata.status is RunSummaryStatus.SUCCEEDED
    assert attempt.metadata.markdown_path == "summary.md"
    assert attempt.metadata.input_tokens == 21
    assert attempt.metadata.output_tokens == 8
    assert manager.summary_markdown_path.read_text().startswith("# Run summary")
    assert resources.agent_values is not None
    assert resources.agent_values["max_tokens"] == RUN_SUMMARY_MAX_TOKENS
    assert resources.agent_values["tools"] == RUN_SUMMARY_TOOLS
    assert resources.process_factory.scope.role is AgentRole.RUN_SUMMARY
    assert resources.process_factory.scope.phase_id is None


@pytest.mark.parametrize("stop_reason", [StopReason.MAX_TOKENS, StopReason.OTHER])
async def test_abnormal_stop_reason_returns_unavailable(tmp_path: Path, stop_reason: StopReason) -> None:
    class IncompleteProcess:
        async def start(self, prompt: str) -> Any:
            return SimpleNamespace(
                final_response=SimpleNamespace(text="# Partial summary", stop_reason=stop_reason),
                total_input_tokens=21,
                total_output_tokens=8,
            )

    summarizer, manager, _ = build_summarizer(tmp_path, IncompleteProcess())

    attempt = await summarizer.summarize(make_outcome(tmp_path))

    assert attempt.metadata.status is RunSummaryStatus.UNAVAILABLE
    assert stop_reason.value in (attempt.metadata.error or "")
    assert attempt.metadata.input_tokens == 21
    assert attempt.metadata.output_tokens == 8
    assert not manager.summary_markdown_path.exists()


async def test_failure_removes_stale_markdown_and_returns_unavailable(tmp_path: Path) -> None:
    class FailingProcess:
        async def start(self, prompt: str) -> Any:
            raise RuntimeError("provider unavailable")

    summarizer, manager, _ = build_summarizer(tmp_path, FailingProcess())
    manager.summary_markdown_path.write_text("stale")

    attempt = await summarizer.summarize(make_outcome(tmp_path))

    assert attempt.metadata.status is RunSummaryStatus.UNAVAILABLE
    assert attempt.metadata.markdown_path is None
    assert "provider unavailable" in (attempt.metadata.error or "")
    assert not manager.summary_markdown_path.exists()


async def test_cancellation_propagates(tmp_path: Path) -> None:
    class CancelledProcess:
        async def start(self, prompt: str) -> Any:
            raise asyncio.CancelledError

    summarizer, _, _ = build_summarizer(tmp_path, CancelledProcess())

    with pytest.raises(asyncio.CancelledError):
        await summarizer.summarize(make_outcome(tmp_path))


async def test_timeout_returns_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class WaitingProcess:
        async def start(self, prompt: str) -> Any:
            await asyncio.Event().wait()

    monkeypatch.setattr("ddev.ai.runtime.summary.RUN_SUMMARY_TIMEOUT_SECONDS", 0.01)
    summarizer, _, _ = build_summarizer(tmp_path, WaitingProcess())

    attempt = await summarizer.summarize(make_outcome(tmp_path))

    assert attempt.metadata.status is RunSummaryStatus.UNAVAILABLE
    assert "TimeoutError" in (attempt.metadata.error or "")


def test_non_summary_roles_still_require_a_phase() -> None:
    from ddev.ai.agent.scope import AgentScope

    with pytest.raises(ValueError, match="must belong to a phase"):
        AgentScope(owner_id="worker", role=AgentRole.PHASE, phase_id=None)
