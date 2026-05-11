# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ddev.ai.phases.agent_phase import AgentPhase, render_memory_prompt, render_task_prompt
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

from .conftest import MockAgent, make_agent_factory, make_response, resolve_key


def _empty_registry_from_names(cls, names, *, owner_id, file_registry):
    return ToolRegistry([])


def _make_agent_phase(
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
    monkeypatch.setattr("ddev.ai.phases.agent_phase.AnthropicAgent", make_agent_factory(mock_agent))
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=tasks or [TaskConfig(name="t1", prompt="Do the work.")],
        checkpoint=checkpoint,
        context_compact_threshold_pct=context_compact_threshold_pct,
    )
    agent_config = AgentConfig(tools=agent_tools or [])
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")

    phase = AgentPhase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=config,
        agent_config=agent_config,
        anthropic_client=MagicMock(),
        checkpoint_manager=checkpoint_manager,
        runtime_variables=runtime_variables or {},
        flow_variables=flow_variables or {},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
        callbacks=None,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


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


def test_render_task_prompt_raises_when_both_unset():
    task = TaskConfig.model_construct(name="t1", prompt=None, prompt_path=None)
    with pytest.raises(FlowConfigError, match="prompt"):
        render_task_prompt(task, None, {})


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


def test_render_memory_prompt_raises_when_both_unset():
    checkpoint = CheckpointConfig.model_construct(memory_prompt=None, memory_prompt_path=None)
    with pytest.raises(FlowConfigError, match="memory_prompt"):
        render_memory_prompt(checkpoint, None, {})


# ---------------------------------------------------------------------------
# AgentPhase.validate_config
# ---------------------------------------------------------------------------


def test_agent_phase_validate_config_rejects_missing_agent():
    config = PhaseConfig(tasks=[TaskConfig(name="t1", prompt="x")])
    with pytest.raises(FlowConfigError, match="requires 'agent'"):
        AgentPhase.validate_config("p1", config, {})


def test_agent_phase_validate_config_rejects_unknown_agent():
    config = PhaseConfig(agent="ghost", tasks=[TaskConfig(name="t1", prompt="x")])
    with pytest.raises(FlowConfigError, match="unknown agent"):
        AgentPhase.validate_config("p1", config, {"writer": AgentConfig()})


def test_agent_phase_validate_config_rejects_empty_tasks():
    config = PhaseConfig(agent="writer")
    with pytest.raises(FlowConfigError, match="at least one task"):
        AgentPhase.validate_config("p1", config, {"writer": AgentConfig()})


def test_agent_phase_validate_config_accepts_valid():
    config = PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="x")])
    AgentPhase.validate_config("p1", config, {"writer": AgentConfig()})


# ---------------------------------------------------------------------------
# AgentPhase.process_message — happy path
# ---------------------------------------------------------------------------


async def test_happy_path_single_task(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),  # task 1 via ReActProcess
        make_response("summary", 10, 5),  # memory step
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.memory_content("p1") == "summary"

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"
    assert checkpoint["tokens"]["total_input"] == 110
    assert checkpoint["tokens"]["total_output"] == 55
    assert checkpoint["memory_path"]

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
    phase, mgr = _make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()["p1"]
    assert checkpoint["tokens"]["total_input"] == 310
    assert checkpoint["tokens"]["total_output"] == 135
    assert checkpoint["memory_path"]


# ---------------------------------------------------------------------------
# AgentPhase.process_message — memory step with checkpoint config
# ---------------------------------------------------------------------------


async def test_memory_step_with_checkpoint_config(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary with files", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        checkpoint=CheckpointConfig(memory_prompt="Also list the files."),
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    memory_prompt = mock_agent.send_calls[1]
    assert "Also list the files." in memory_prompt
    assert "Write a brief summary" in memory_prompt


async def test_memory_step_without_checkpoint_config(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    memory_prompt = mock_agent.send_calls[1]
    assert memory_prompt == "Write a brief summary of what you accomplished in this phase."


# ---------------------------------------------------------------------------
# AgentPhase.process_message — context compaction between tasks
# ---------------------------------------------------------------------------


async def test_compact_between_tasks_when_above_threshold(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task1 done", 100, 50, context_pct=85),  # above 80% threshold
        make_response("task2 done", 200, 80),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"
    assert checkpoint["memory_path"]
    assert mock_agent.compact_call_count >= 1


async def test_no_compact_when_below_threshold(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task1 done", 100, 50, context_pct=50),  # below 80% threshold
        make_response("task2 done", 200, 80),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First task."),
            TaskConfig(name="t2", prompt="Second task."),
        ],
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))
    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"
    assert checkpoint["memory_path"]
    assert mock_agent.compact_call_count == 0


# ---------------------------------------------------------------------------
# AgentPhase.process_message — template context
# ---------------------------------------------------------------------------


async def test_flow_variables_in_system_prompt(flow_dir, monkeypatch, message_queue):
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

    monkeypatch.setattr("ddev.ai.phases.agent_phase.AnthropicAgent", capturing_factory)
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
    )
    phase = AgentPhase(
        phase_id="p1",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=CheckpointManager(flow_dir / "checkpoints.yaml"),
        runtime_variables={},
        flow_variables={"project": "myproj"},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
    )
    phase.queue = message_queue

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

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

    monkeypatch.setattr("ddev.ai.phases.agent_phase.AnthropicAgent", capturing_factory)
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
    )
    phase = AgentPhase(
        phase_id="p1",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=CheckpointManager(flow_dir / "checkpoints.yaml"),
        runtime_variables={"project": "runtime_override"},
        flow_variables={"project": "flow_default"},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
    )
    phase.queue = message_queue

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured_kwargs["system_prompt"] == "Project: runtime_override"


# ---------------------------------------------------------------------------
# AgentPhase.process_message — before_react / after_react errors
# ---------------------------------------------------------------------------


async def test_before_react_raises_propagates(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([])
    phase, _ = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    def failing_hook():
        raise RuntimeError("setup failed")

    phase.before_react = failing_hook

    with pytest.raises(RuntimeError, match="setup failed"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


async def test_after_react_raises_propagates(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("done", 100, 50),
    ]
    mock_agent = MockAgent(responses)
    phase, _ = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    def failing_hook():
        raise RuntimeError("teardown failed")

    phase.after_react = failing_hook

    with pytest.raises(RuntimeError, match="teardown failed"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))


# ---------------------------------------------------------------------------
# AgentPhase.process_message — resolver integration with memory files
# ---------------------------------------------------------------------------


async def test_task_prompt_resolves_memory_variable(flow_dir, monkeypatch, message_queue):
    mgr = CheckpointManager(flow_dir / "checkpoints.yaml")
    mgr.write_phase_checkpoint("draft", {"status": "success"})
    mgr.write_memory("draft", "Created file.py")

    responses = [
        make_response("done", 100, 50),
        make_response("summary", 10, 5),
    ]
    mock_agent = MockAgent(responses)

    monkeypatch.setattr("ddev.ai.phases.agent_phase.AnthropicAgent", make_agent_factory(mock_agent))
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Review: ${draft_memory}")],
    )
    phase = AgentPhase(
        phase_id="review",
        dependencies=[],
        config=config,
        agent_config=AgentConfig(),
        anthropic_client=MagicMock(),
        checkpoint_manager=mgr,
        runtime_variables={},
        flow_variables={},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
    )
    phase.queue = message_queue

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mock_agent.send_calls[0] == "Review: Created file.py"


# ---------------------------------------------------------------------------
# AgentPhase.process_message — memory step failure behaviour
# ---------------------------------------------------------------------------


async def test_memory_api_failure_fails_phase(flow_dir, monkeypatch, message_queue):
    responses = [make_response("task done", 100, 50)]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    with pytest.raises(IndexError):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


async def test_memory_template_error_fails_phase(flow_dir, monkeypatch, message_queue):
    responses = [make_response("task done", 100, 50)]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        checkpoint=CheckpointConfig(memory_prompt="Summarize."),
    )

    def raise_render_error(*args, **kwargs):
        raise ValueError("template error")

    monkeypatch.setattr("ddev.ai.phases.agent_phase.render_memory_prompt", raise_render_error)

    with pytest.raises(ValueError, match="template error"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


async def test_successful_phase_writes_memory_path_into_checkpoint(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary text", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    checkpoint = mgr.read()["p1"]
    assert "memory_path" in checkpoint
    memory_path = Path(checkpoint["memory_path"])
    assert memory_path.is_absolute()
    assert memory_path.exists()
    assert memory_path.name == "p1_memory.md"
    assert memory_path.read_text() == "summary text"


async def test_write_memory_disk_failure_fails_phase(flow_dir, monkeypatch, message_queue):
    responses = [
        make_response("task done", 100, 50),
        make_response("summary text", 10, 5),
    ]
    mock_agent = MockAgent(responses)
    phase, mgr = _make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    def raise_permission_error(*args, **kwargs):
        raise PermissionError("disk is read-only")

    monkeypatch.setattr("ddev.ai.phases.checkpoint.CheckpointManager.write_memory", raise_permission_error)

    with pytest.raises(PermissionError, match="disk is read-only"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}
