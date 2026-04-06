# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Integration tests: 3-phase sequential pipeline run through a real
EventBusOrchestrator with mocked agents.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from ddev.ai.phases.base import Phase
from ddev.ai.phases.messages import (
    PhaseCompleteMessage,
    PhaseFailedMessage,
    PipelineStartMessage,
    make_phase_complete_type,
)
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator

from .conftest import MockAgent, build_phase_config, make_agent_factory, make_response

# ---------------------------------------------------------------------------
# Minimal test orchestrator
# ---------------------------------------------------------------------------


class _TestOrchestrator(EventBusOrchestrator):
    """Concrete EventBusOrchestrator for tests.

    Submits PipelineStartMessage on init, stops on PhaseFailedMessage.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        metadata: dict[str, Any],
    ) -> None:
        super().__init__(
            logger=logging.getLogger("test_orchestrator"),
            max_timeout=30,
            grace_period=0,
        )
        self._checkpoint_path = checkpoint_path
        self._metadata = metadata
        self.received_message_types: list[type] = []
        self.failed = False

    async def on_initialize(self) -> None:
        self.submit_message(
            PipelineStartMessage(
                id="pipeline_start",
                checkpoint_path=str(self._checkpoint_path),
                metadata=self._metadata,
            )
        )

    async def on_message_received(self, message: BaseMessage) -> None:
        self.received_message_types.append(type(message))
        if isinstance(message, PhaseFailedMessage):
            self.failed = True
            raise FatalProcessingError(f"Phase failed: {message.error}")

    async def on_finalize(self, exception: Exception | None) -> None:
        pass


def _run_pipeline(
    tmp_path: Path,
    phases: list[Phase],
    metadata: dict[str, Any] | None = None,
) -> _TestOrchestrator:
    """Register phases, run the orchestrator, and return it for assertions."""
    checkpoint_path = tmp_path / "checkpoints.yaml"
    orchestrator = _TestOrchestrator(checkpoint_path, metadata or {"project": "test"})

    # Generate typed completion messages and wire subscriptions
    phase_names = [p.name for p in phases]
    complete_types = [make_phase_complete_type(name) for name in phase_names]

    # First phase subscribes to PipelineStartMessage
    orchestrator.register_processor(phases[0], [PipelineStartMessage])
    # Subsequent phases subscribe to the previous phase's completion type
    for phase, upstream_type in zip(phases[1:], complete_types, strict=False):
        orchestrator.register_processor(phase, [upstream_type])

    orchestrator.run()
    return orchestrator


# ---------------------------------------------------------------------------
# Successful 3-phase pipeline
# ---------------------------------------------------------------------------


def test_three_phase_pipeline_all_succeed(tmp_path):
    phases = [
        Phase(
            config=build_phase_config(
                tmp_path,
                name="analyze",
                checkpoint_schema={"items": 0},
            ),
            agent_factory=make_agent_factory(MockAgent([make_response("items: 3")])),
        ),
        Phase(
            config=build_phase_config(
                tmp_path,
                name="transform",
                checkpoint_schema={"transformed": 0},
            ),
            agent_factory=make_agent_factory(MockAgent([make_response("transformed: 3")])),
        ),
        Phase(
            config=build_phase_config(
                tmp_path,
                name="finalize",
                checkpoint_schema={"done": False},
            ),
            agent_factory=make_agent_factory(MockAgent([make_response("done: true")])),
        ),
    ]

    orchestrator = _run_pipeline(tmp_path, phases)

    assert not orchestrator.failed
    data = yaml.safe_load((tmp_path / "checkpoints.yaml").read_text())
    assert data["analyze"]["status"] == "success"
    assert data["transform"]["status"] == "success"
    assert data["finalize"]["status"] == "success"


def test_checkpoints_accumulate_across_all_phases(tmp_path):
    phases = [
        Phase(
            config=build_phase_config(tmp_path, name="p1", checkpoint_schema={"a": 0}),
            agent_factory=make_agent_factory(MockAgent([make_response("a: 1")])),
        ),
        Phase(
            config=build_phase_config(tmp_path, name="p2", checkpoint_schema={"b": 0}),
            agent_factory=make_agent_factory(MockAgent([make_response("b: 2")])),
        ),
        Phase(
            config=build_phase_config(tmp_path, name="p3", checkpoint_schema={"c": 0}),
            agent_factory=make_agent_factory(MockAgent([make_response("c: 3")])),
        ),
    ]

    _run_pipeline(tmp_path, phases)

    data = yaml.safe_load((tmp_path / "checkpoints.yaml").read_text())
    assert "p1" in data and "p2" in data and "p3" in data
    assert data["p1"]["a"] == 1
    assert data["p2"]["b"] == 2
    assert data["p3"]["c"] == 3


def test_downstream_phase_sees_upstream_checkpoint_in_prompt(tmp_path):
    """Phase 2's task prompt injects {{ checkpoint_data }}, so it should contain phase 1's output."""
    captured_prompts: list[str] = []

    class CapturingAgent(MockAgent):
        async def send(self, content, allowed_tools=None):
            if isinstance(content, str):
                captured_prompts.append(content)
            return await super().send(content, allowed_tools)

    phases = [
        Phase(
            config=build_phase_config(tmp_path, name="src", checkpoint_schema={"marker": ""}),
            agent_factory=make_agent_factory(MockAgent([make_response("marker: FOUND_IT")])),
        ),
        Phase(
            config=build_phase_config(
                tmp_path,
                name="dst",
                checkpoint_schema={"done": False},
                task_prompt="Previous output:\n{{ checkpoint_data }}\nDone.",
            ),
            agent_factory=make_agent_factory(CapturingAgent([make_response("done: true")])),
        ),
    ]

    _run_pipeline(tmp_path, [phases[0], phases[1]])

    assert any("FOUND_IT" in p for p in captured_prompts), "Phase 2's prompt should contain Phase 1's checkpoint output"


# ---------------------------------------------------------------------------
# Failure scenarios
# ---------------------------------------------------------------------------


def test_pipeline_stops_when_phase_fails(tmp_path):
    """A phase that returns invalid YAML causes the pipeline to stop via PhaseFailedMessage."""
    phases = [
        Phase(
            config=build_phase_config(tmp_path, name="fail_phase", checkpoint_schema={"key": ""}),
            agent_factory=make_agent_factory(MockAgent([make_response(": invalid yaml :")])),
        ),
        Phase(
            config=build_phase_config(tmp_path, name="never_runs", checkpoint_schema={}),
            agent_factory=make_agent_factory(MockAgent([make_response("ok: true")])),
        ),
    ]

    orchestrator = _run_pipeline(tmp_path, phases)

    assert orchestrator.failed
    # The second phase never ran — its checkpoint section should not exist
    checkpoint_path = tmp_path / "checkpoints.yaml"
    if checkpoint_path.exists():
        data = yaml.safe_load(checkpoint_path.read_text())
        assert "never_runs" not in data


def test_failed_phase_writes_failed_status_to_checkpoint(tmp_path):
    phases = [
        Phase(
            config=build_phase_config(tmp_path, name="bad_phase", checkpoint_schema={"key": ""}),
            agent_factory=make_agent_factory(MockAgent([make_response("- not a mapping")])),
        ),
    ]

    _run_pipeline(tmp_path, [phases[0]])

    checkpoint_path = tmp_path / "checkpoints.yaml"
    assert checkpoint_path.exists()
    data = yaml.safe_load(checkpoint_path.read_text())
    assert data["bad_phase"]["status"] == "failed"
    assert "error" in data["bad_phase"]


# ---------------------------------------------------------------------------
# Message dispatch correctness
# ---------------------------------------------------------------------------


def test_each_phase_only_wakes_its_subscriber(tmp_path):
    """
    Verify that completion messages use unique types so each phase only wakes
    up the one processor subscribed to it.

    We track which message types the orchestrator received and assert that
    the subscribed types are all distinct subclasses.
    """
    names = ["dispatch_a", "dispatch_b", "dispatch_c"]
    phases = [
        Phase(
            config=build_phase_config(tmp_path, name=name, checkpoint_schema={}),
            agent_factory=make_agent_factory(MockAgent([make_response("ok: true")])),
        )
        for name in names
    ]

    orchestrator = _run_pipeline(tmp_path, phases)

    # Collect PhaseCompleteMessage subclasses that were dispatched
    complete_types = [t for t in orchestrator.received_message_types if issubclass(t, PhaseCompleteMessage)]

    # All 3 completion types must be distinct
    assert len(set(complete_types)) == 3

    # Each is a unique subclass, not the base class itself
    for t in complete_types:
        assert t is not PhaseCompleteMessage
        assert issubclass(t, PhaseCompleteMessage)
