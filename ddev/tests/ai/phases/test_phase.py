# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

import pytest
import yaml

from ddev.ai.phases.base import Phase
from ddev.ai.phases.checkpoint import CheckpointValidationError
from ddev.ai.phases.messages import (
    PhaseCompleteMessage,
    PhaseFailedMessage,
    PipelineStartMessage,
    make_phase_complete_type,
)

from .conftest import MockAgent, build_phase_config, make_agent_factory, make_capturing_agent_factory, make_response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _start_message(checkpoint_path: str, metadata: dict | None = None) -> PipelineStartMessage:
    return PipelineStartMessage(
        id="start",
        checkpoint_path=checkpoint_path,
        metadata=metadata or {"project": "test"},
    )


def _make_phase(tmp_path, agent: MockAgent, **kwargs) -> Phase:
    config = build_phase_config(tmp_path, **kwargs)
    phase = Phase(config=config, agent_factory=make_agent_factory(agent))
    phase.queue = asyncio.Queue()
    return phase


# ---------------------------------------------------------------------------
# process_message — happy path
# ---------------------------------------------------------------------------


async def test_process_message_calls_agent_once_per_task(tmp_path):
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent, num_tasks=1)
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert len(agent.send_calls) == 1


async def test_process_message_calls_agent_once_per_task_multi(tmp_path):
    agent = MockAgent([make_response("key: value"), make_response("key: value")])
    phase = _make_phase(tmp_path, agent, num_tasks=2)
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert len(agent.send_calls) == 2


async def test_process_message_writes_success_checkpoint(tmp_path):
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("items: 5\nstatus: done")])
    phase = _make_phase(
        tmp_path,
        agent,
        checkpoint_schema={"items": 0, "status": ""},
    )
    await phase.process_message(_start_message(str(checkpoint)))
    data = yaml.safe_load(checkpoint.read_text())
    assert data["test_phase"]["status"] == "success"
    assert data["test_phase"]["items"] == 5


async def test_process_message_adds_status_success_to_checkpoint(tmp_path):
    """The phase injects status: success even if the agent response doesn't include it."""
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("result: ok")])
    phase = _make_phase(tmp_path, agent, checkpoint_schema={"result": ""})
    await phase.process_message(_start_message(str(checkpoint)))
    data = yaml.safe_load(checkpoint.read_text())
    assert data["test_phase"]["status"] == "success"


async def test_process_message_injects_metadata_into_task_prompt(tmp_path):
    """The task prompt template receives metadata from the start message."""
    checkpoint = tmp_path / "c.yaml"

    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(
        tmp_path,
        agent,
        task_prompt="Project is {{ metadata.project }}.",
    )
    await phase.process_message(_start_message(str(checkpoint), metadata={"project": "myapp"}))
    rendered_prompt = agent.send_calls[0]
    assert "myapp" in rendered_prompt


async def test_process_message_renders_system_prompt_with_template_variables(tmp_path):
    """The system prompt template is rendered with Jinja2 before being passed to the agent factory."""
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("key: value")])
    factory, captured_prompts = make_capturing_agent_factory(agent)
    config = build_phase_config(
        tmp_path,
        system_prompt="Agent for {{ metadata.project }} v{{ metadata.version }}.",
    )
    phase = Phase(config=config, agent_factory=factory)
    phase.queue = asyncio.Queue()
    await phase.process_message(_start_message(str(checkpoint), metadata={"project": "myapp", "version": "3"}))
    assert len(captured_prompts) == 1
    assert "myapp" in captured_prompts[0]
    assert "3" in captured_prompts[0]


async def test_process_message_injects_checkpoint_data_into_task_prompt(tmp_path):
    """checkpoint_data from a prior phase is visible in the task prompt template."""
    checkpoint = tmp_path / "c.yaml"
    # Pre-populate checkpoint with a prior phase result
    checkpoint.write_text(yaml.dump({"prior_phase": {"status": "success", "items": 42}}))

    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(
        tmp_path,
        agent,
        task_prompt="Prior data: {{ checkpoint_data }}",
    )
    await phase.process_message(_start_message(str(checkpoint)))
    rendered_prompt = agent.send_calls[0]
    assert "prior_phase" in rendered_prompt
    assert "42" in rendered_prompt


# ---------------------------------------------------------------------------
# process_message — validation failures
# ---------------------------------------------------------------------------


async def test_process_message_raises_on_invalid_yaml_response(tmp_path):
    agent = MockAgent([make_response(": : invalid yaml")])
    phase = _make_phase(tmp_path, agent, checkpoint_schema={"key": ""})
    with pytest.raises(CheckpointValidationError):
        await phase.process_message(_start_message(str(tmp_path / "c.yaml")))


async def test_process_message_raises_on_missing_schema_keys(tmp_path):
    agent = MockAgent([make_response("only_one_key: value")])
    phase = _make_phase(
        tmp_path,
        agent,
        checkpoint_schema={"only_one_key": "", "missing_key": ""},
    )
    with pytest.raises(CheckpointValidationError, match="missing_key"):
        await phase.process_message(_start_message(str(tmp_path / "c.yaml")))


async def test_process_message_raises_on_non_mapping_response(tmp_path):
    agent = MockAgent([make_response("- item1\n- item2")])
    phase = _make_phase(tmp_path, agent, checkpoint_schema={"key": ""})
    with pytest.raises(CheckpointValidationError, match="mapping"):
        await phase.process_message(_start_message(str(tmp_path / "c.yaml")))


# ---------------------------------------------------------------------------
# Context reset
# ---------------------------------------------------------------------------


async def test_agent_reset_called_when_context_exceeds_threshold(tmp_path):
    # First prompt: context at 85% (above default 80% threshold)
    # Second prompt: should trigger reset before being sent
    agent = MockAgent(
        [
            make_response("key: value", context_pct=85.0),
            make_response("key: value"),
        ]
    )
    phase = _make_phase(tmp_path, agent, num_tasks=2)
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert agent.reset_count == 1


async def test_agent_reset_not_called_when_context_below_threshold(tmp_path):
    agent = MockAgent(
        [
            make_response("key: value", context_pct=50.0),
            make_response("key: value"),
        ]
    )
    phase = _make_phase(tmp_path, agent, num_tasks=2)
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert agent.reset_count == 0


async def test_agent_reset_not_called_on_first_prompt(tmp_path):
    """Reset is only checked after the first prompt, never before it."""
    agent = MockAgent([make_response("key: value", context_pct=99.0)])
    phase = _make_phase(tmp_path, agent, num_tasks=1)
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert agent.reset_count == 0


async def test_context_reset_threshold_respects_config(tmp_path):
    """A phase with threshold=50 resets at 60%, while default 80% would not."""
    agent = MockAgent(
        [
            make_response("key: value", context_pct=60.0),
            make_response("key: value"),
        ]
    )
    phase = _make_phase(
        tmp_path,
        agent,
        num_tasks=2,
        agent_overrides={"context_reset_threshold_pct": 50},
    )
    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))
    assert agent.reset_count == 1


# ---------------------------------------------------------------------------
# on_success
# ---------------------------------------------------------------------------


async def test_on_success_emits_unique_phase_complete_subclass(tmp_path):
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    msg = _start_message(str(tmp_path / "c.yaml"))
    await phase.process_message(msg)
    await phase.on_success(msg)

    emitted = phase.queue.get_nowait()
    expected_type = make_phase_complete_type("test_phase")
    assert type(emitted) is expected_type


async def test_on_success_emitted_message_is_phase_complete_instance(tmp_path):
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    msg = _start_message(str(tmp_path / "c.yaml"))
    await phase.process_message(msg)
    await phase.on_success(msg)

    emitted = phase.queue.get_nowait()
    assert isinstance(emitted, PhaseCompleteMessage)


async def test_on_success_forwards_checkpoint_path(tmp_path):
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    msg = _start_message(str(checkpoint))
    await phase.process_message(msg)
    await phase.on_success(msg)

    emitted = phase.queue.get_nowait()
    assert emitted.checkpoint_path == str(checkpoint)


async def test_on_success_forwards_metadata(tmp_path):
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    msg = _start_message(str(tmp_path / "c.yaml"), metadata={"project": "myapp", "version": "2"})
    await phase.process_message(msg)
    await phase.on_success(msg)

    emitted = phase.queue.get_nowait()
    assert emitted.metadata == {"project": "myapp", "version": "2"}


async def test_on_success_sets_phase_name_on_message(tmp_path):
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent, name="my_special_phase")
    msg = _start_message(str(tmp_path / "c.yaml"))
    await phase.process_message(msg)
    await phase.on_success(msg)

    emitted = phase.queue.get_nowait()
    assert emitted.phase_name == "my_special_phase"


# ---------------------------------------------------------------------------
# on_error
# ---------------------------------------------------------------------------


async def test_on_error_writes_failed_checkpoint(tmp_path):
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    phase._checkpoint_path = checkpoint  # simulate that process_message started
    msg = _start_message(str(checkpoint))

    await phase.on_error(msg, ValueError("something went wrong"))

    data = yaml.safe_load(checkpoint.read_text())
    assert data["test_phase"]["status"] == "failed"
    assert "something went wrong" in data["test_phase"]["error"]


async def test_on_error_emits_phase_failed_message(tmp_path):
    checkpoint = tmp_path / "c.yaml"
    agent = MockAgent([make_response("key: value")])
    phase = _make_phase(tmp_path, agent)
    phase._checkpoint_path = checkpoint
    msg = _start_message(str(checkpoint))

    await phase.on_error(msg, RuntimeError("boom"))

    emitted = phase.queue.get_nowait()
    assert isinstance(emitted, PhaseFailedMessage)
    assert "boom" in emitted.error


async def test_on_error_with_no_checkpoint_path_still_emits_failed_message(tmp_path):
    """If process_message failed before setting checkpoint_path, on_error still emits."""
    agent = MockAgent([])
    phase = _make_phase(tmp_path, agent)
    # _checkpoint_path is None by default (never set)
    msg = _start_message(str(tmp_path / "c.yaml"))

    await phase.on_error(msg, RuntimeError("early failure"))

    emitted = phase.queue.get_nowait()
    assert isinstance(emitted, PhaseFailedMessage)
    assert emitted.phase_name == "test_phase"


async def test_on_error_does_not_write_checkpoint_when_path_is_none(tmp_path):
    agent = MockAgent([])
    phase = _make_phase(tmp_path, agent)
    # _checkpoint_path is None
    msg = _start_message(str(tmp_path / "c.yaml"))
    checkpoint = tmp_path / "c.yaml"

    await phase.on_error(msg, RuntimeError("early"))

    assert not checkpoint.exists()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


async def test_callbacks_are_fired_during_react_loop(tmp_path):
    """Callbacks passed to Phase are forwarded to ReActProcess and fire on each agent response."""

    class _RecordingCallback:
        def __init__(self) -> None:
            self.response_count = 0
            self.complete_count = 0

        async def on_agent_response(self, response, iteration) -> None:
            self.response_count += 1

        async def on_tool_call(self, tool_call, result, iteration) -> None:
            pass

        async def on_complete(self, result) -> None:
            self.complete_count += 1

        async def on_error(self, error) -> None:
            pass

    recording = _RecordingCallback()
    agent = MockAgent([make_response("key: value")])
    config = build_phase_config(tmp_path)
    phase = Phase(config=config, agent_factory=make_agent_factory(agent), callbacks=[recording])
    phase.queue = asyncio.Queue()

    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))

    assert recording.response_count == 1
    assert recording.complete_count == 1


async def test_callbacks_fire_once_per_task(tmp_path):
    """With 2 task prompts, callbacks fire once per react.start() call."""

    class _RecordingCallback:
        def __init__(self) -> None:
            self.complete_count = 0

        async def on_agent_response(self, response, iteration) -> None:
            pass

        async def on_tool_call(self, tool_call, result, iteration) -> None:
            pass

        async def on_complete(self, result) -> None:
            self.complete_count += 1

        async def on_error(self, error) -> None:
            pass

    recording = _RecordingCallback()
    agent = MockAgent([make_response("key: value"), make_response("key: value")])
    config = build_phase_config(tmp_path, num_tasks=2)
    phase = Phase(config=config, agent_factory=make_agent_factory(agent), callbacks=[recording])
    phase.queue = asyncio.Queue()

    await phase.process_message(_start_message(str(tmp_path / "c.yaml")))

    assert recording.complete_count == 2
