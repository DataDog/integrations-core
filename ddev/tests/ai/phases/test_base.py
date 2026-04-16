# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.phases.base import Phase, _make_memory_resolver, render_memory_prompt, render_task_prompt
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseFinishedMessage, StartMessage
from ddev.ai.tools.core.registry import ToolRegistry

from .conftest import MockAgent, make_agent_factory, make_response, resolve_key


def _empty_registry_from_names(cls, names):
    return ToolRegistry([])


# ---------------------------------------------------------------------------
# _make_memory_resolver
# ---------------------------------------------------------------------------


def test_resolver_memory_suffix(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    mgr.write_phase_checkpoint("x", {})
    mgr.write_memory("draft", "Draft memory content.")
    resolver = _make_memory_resolver(mgr)
    assert resolver("draft_memory") == "Draft memory content."


def test_resolver_non_memory_key():
    mgr = MagicMock()
    resolver = _make_memory_resolver(mgr)
    assert resolver("some_variable") == "<VARIABLE UNDEFINED: some_variable>"
    mgr.get_memory.assert_not_called()


def test_resolver_absent_memory(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    resolver = _make_memory_resolver(mgr)
    assert resolver("nonexistent_memory") == "<MEMORY NOT FOUND: nonexistent>"


# ---------------------------------------------------------------------------
# render_task_prompt
# ---------------------------------------------------------------------------


def test_render_task_prompt_from_file(tmp_path):
    prompt_file = tmp_path / "task.md"
    prompt_file.write_text("Hello ${name}.")
    task = TaskConfig(name="t1", prompt_path="task.md")
    result = render_task_prompt(task, tmp_path, {"name": "Alice"})
    assert result == "Hello Alice."


def test_render_task_prompt_inline():
    task = TaskConfig(name="t1", prompt="Hello ${name}.")
    result = render_task_prompt(task, None, {"name": "Bob"})
    assert result == "Hello Bob."


def test_render_task_prompt_forwards_resolver(tmp_path):
    prompt_file = tmp_path / "task.md"
    prompt_file.write_text("Memory: ${draft_memory}")
    task = TaskConfig(name="t1", prompt_path="task.md")
    result = render_task_prompt(task, tmp_path, {}, resolve_key)
    assert result == "Memory: resolved(draft_memory)"


# ---------------------------------------------------------------------------
# render_memory_prompt
# ---------------------------------------------------------------------------


def test_render_memory_prompt_from_file(tmp_path):
    mem_file = tmp_path / "mem.md"
    mem_file.write_text("List files for ${phase_name}.")
    checkpoint = CheckpointConfig(memory_prompt_path="mem.md")
    result = render_memory_prompt(checkpoint, tmp_path, {"phase_name": "draft"})
    assert result == "List files for draft."


def test_render_memory_prompt_inline():
    checkpoint = CheckpointConfig(memory_prompt="List files for ${phase_name}.")
    result = render_memory_prompt(checkpoint, None, {"phase_name": "draft"})
    assert result == "List files for draft."


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------


def _make_phase(
    flow_dir,
    mock_agent,
    monkeypatch,
    message_queue,
    *,
    phase_id="p1",
    dependencies=None,
    tasks=None,
    checkpoint=None,
    agent_tools=None,
    flow_variables=None,
    runtime_variables=None,
    context_compact_threshold_pct=80,
):
    monkeypatch.setattr("ddev.ai.phases.base.AnthropicAgent", make_agent_factory(mock_agent))
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=tasks or [TaskConfig(name="t1", prompt="Do the work.")],
        checkpoint=checkpoint,
        context_compact_threshold_pct=context_compact_threshold_pct,
    )
    agent_config = AgentConfig(tools=agent_tools or [])
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")

    phase = Phase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=config,
        agent_config=agent_config,
        anthropic_client=MagicMock(),
        checkpoint_manager=checkpoint_manager,
        runtime_variables=runtime_variables or {},
        flow_variables=flow_variables or {},
        config_dir=flow_dir,
        callback_sets=None,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


# ---------------------------------------------------------------------------
# Phase.process_message — happy path
# ---------------------------------------------------------------------------


async def test_happy_path_single_task(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),  # task 1 via ReActProcess
        make_response("summary", 10, 5),  # memory step
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(StartMessage(id="start"))

    # Memory was written
    assert mgr.get_memory("p1") == "summary"

    # Checkpoint was written
    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"
    assert checkpoint["tokens"]["total_input"] == 110
    assert checkpoint["tokens"]["total_output"] == 55

    # on_success is called by _task_wrapper, not process_message directly.
    # But we verify it would work by checking the send calls.
    assert len(mock_agent.send_calls) == 2
    assert mock_agent.send_calls[0] == "Do the work."
    assert "Write a brief summary" in mock_agent.send_calls[1]


async def test_happy_path_two_tasks(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task1 done", 100, 50),
        make_response("task2 done", 200, 80),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(StartMessage(id="start"))

    checkpoint = mgr.read()["p1"]
    assert checkpoint["tokens"]["total_input"] == 310
    assert checkpoint["tokens"]["total_output"] == 135


# ---------------------------------------------------------------------------
# Phase.process_message — relevance check
# ---------------------------------------------------------------------------


async def test_irrelevant_message_returns_immediately(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])  # no responses needed — should never be called
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        dependencies=["other_phase"],
    )

    # Send a PhaseFinishedMessage from a phase that's NOT a dependency
    msg = PhaseFinishedMessage(id="msg1", phase_id="unrelated_phase")
    await phase.process_message(msg)

    # No sends, no checkpoint
    assert mock_agent.send_calls == []
    assert mgr.read() == {}


async def test_waits_for_all_dependencies(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        dependencies=["dep1", "dep2"],
    )

    # First dependency arrives — phase should NOT execute yet
    msg1 = PhaseFinishedMessage(id="msg1", phase_id="dep1")
    await phase.process_message(msg1)
    assert mock_agent.send_calls == []

    # Second dependency arrives — phase should execute
    msg2 = PhaseFinishedMessage(id="msg2", phase_id="dep2")
    await phase.process_message(msg2)
    assert len(mock_agent.send_calls) == 2


async def test_does_not_re_execute_after_completion(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        dependencies=["dep1"],
    )

    # First execution
    msg1 = PhaseFinishedMessage(id="msg1", phase_id="dep1")
    await phase.process_message(msg1)
    assert len(mock_agent.send_calls) == 2

    # Second message for the same dep — phase must NOT re-execute
    msg2 = PhaseFinishedMessage(id="msg2", phase_id="dep1")
    await phase.process_message(msg2)
    assert len(mock_agent.send_calls) == 2  # unchanged


# ---------------------------------------------------------------------------
# Phase.process_message — memory step with checkpoint config
# ---------------------------------------------------------------------------


async def test_memory_step_with_checkpoint_config(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary with files", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        checkpoint=CheckpointConfig(memory_prompt="Also list the files."),
    )

    await phase.process_message(StartMessage(id="start"))

    # Memory prompt should include user additions
    memory_prompt = mock_agent.send_calls[1]
    assert "Also list the files." in memory_prompt
    assert "Write a brief summary" in memory_prompt


async def test_memory_step_without_checkpoint_config(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(StartMessage(id="start"))

    memory_prompt = mock_agent.send_calls[1]
    assert memory_prompt == "Write a brief summary of what you accomplished in this phase."


# ---------------------------------------------------------------------------
# Phase.process_message — context compaction between tasks
# ---------------------------------------------------------------------------


async def test_compact_between_tasks_when_above_threshold(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task1 done", 100, 50, context_pct=85),  # above 80% threshold
        make_response("task2 done", 200, 80),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(StartMessage(id="start"))

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"


async def test_no_compact_when_below_threshold(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task1 done", 100, 50, context_pct=50),  # below 80% threshold
        make_response("task2 done", 200, 80),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(StartMessage(id="start"))
    assert mgr.read()["p1"]["status"] == "success"


# ---------------------------------------------------------------------------
# Phase.process_message — template context
# ---------------------------------------------------------------------------


async def test_flow_variables_in_system_prompt(flow_dir, monkeypatch, message_queue):
    # System prompt references ${project}
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}")
    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    captured_kwargs = {}
    original_factory = make_agent_factory(mock_agent)

    def capturing_factory(**kwargs):
        captured_kwargs.update(kwargs)
        return original_factory(**kwargs)

    monkeypatch.setattr("ddev.ai.phases.base.AnthropicAgent", capturing_factory)
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
    )
    phase = Phase(
        phase_id="p1",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=CheckpointManager(flow_dir / "checkpoints.yaml"),
        runtime_variables={},
        flow_variables={"project": "myproj"},
        config_dir=flow_dir,
    )
    phase.queue = message_queue

    await phase.process_message(StartMessage(id="start"))

    assert "Project: myproj" == captured_kwargs["system_prompt"]


async def test_runtime_variables_override_flow_variables(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}")
    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    captured_kwargs = {}
    original_factory = make_agent_factory(mock_agent)

    def capturing_factory(**kwargs):
        captured_kwargs.update(kwargs)
        return original_factory(**kwargs)

    monkeypatch.setattr("ddev.ai.phases.base.AnthropicAgent", capturing_factory)
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
    )
    phase = Phase(
        phase_id="p1",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=CheckpointManager(flow_dir / "checkpoints.yaml"),
        runtime_variables={"project": "runtime_override"},
        flow_variables={"project": "flow_default"},
        config_dir=flow_dir,
    )
    phase.queue = message_queue

    await phase.process_message(StartMessage(id="start"))

    assert captured_kwargs["system_prompt"] == "Project: runtime_override"


# ---------------------------------------------------------------------------
# Phase.process_message — before_react / after_react errors
# ---------------------------------------------------------------------------


async def test_before_react_raises_propagates(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    def failing_hook():
        raise RuntimeError("setup failed")

    phase.before_react = failing_hook

    with pytest.raises(RuntimeError, match="setup failed"):
        await phase.process_message(StartMessage(id="start"))


async def test_after_react_raises_propagates(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("done", 100, 50),
    ]
    mock_agent = MockAgent(responses)
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    def failing_hook():
        raise RuntimeError("teardown failed")

    phase.after_react = failing_hook

    with pytest.raises(RuntimeError, match="teardown failed"):
        await phase.process_message(StartMessage(id="start"))


# ---------------------------------------------------------------------------
# Phase.on_success
# ---------------------------------------------------------------------------


async def test_on_success_emits_finished_message(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)
    phase._executed = True  # simulate that process_message ran the full pipeline

    await phase.on_success(StartMessage(id="start"))

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFinishedMessage)
    assert msg.phase_id == "p1"
    assert msg.id == "p1_finished_start"


async def test_on_success_skips_when_not_executed(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.on_success(StartMessage(id="start"))

    assert message_queue.empty()


async def test_on_success_emits_only_once(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)
    phase._executed = True

    await phase.on_success(StartMessage(id="msg1"))
    await phase.on_success(StartMessage(id="msg2"))

    assert message_queue.qsize() == 1


# ---------------------------------------------------------------------------
# Phase.on_error
# ---------------------------------------------------------------------------


async def test_on_error_writes_failed_checkpoint(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, mgr = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.on_error(StartMessage(id="start"), RuntimeError("boom"))

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "failed"
    assert checkpoint["error"] == "boom"
    assert checkpoint["started_at"] is None  # not started yet


async def test_on_error_emits_failed_message(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.on_error(StartMessage(id="start"), RuntimeError("boom"))

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)
    assert msg.phase_id == "p1"
    assert msg.error == "boom"


# ---------------------------------------------------------------------------
# Phase.process_message — resolver integration with memory files
# ---------------------------------------------------------------------------


async def test_task_prompt_resolves_memory_variable(flow_dir, monkeypatch, message_queue):
    # Create a memory file for "draft" phase
    mgr = CheckpointManager(flow_dir / "checkpoints.yaml")
    mgr.write_phase_checkpoint("draft", {"status": "success"})
    mgr.write_memory("draft", "Created file.py")

    # Task prompt references ${draft_memory}
    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)

    monkeypatch.setattr("ddev.ai.phases.base.AnthropicAgent", make_agent_factory(mock_agent))
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Review: ${draft_memory}")],
    )
    phase = Phase(
        phase_id="review",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=mgr,
        runtime_variables={},
        flow_variables={},
        config_dir=flow_dir,
    )
    phase.queue = message_queue

    await phase.process_message(StartMessage(id="start"))

    assert mock_agent.send_calls[0] == "Review: Created file.py"
