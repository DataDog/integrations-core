# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.phases.agentic_phase import AgenticPhase, render_memory_prompt, render_task_prompt
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

from .conftest import MockAgent, make_agent_phase, make_response, resolve_key


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# render_task_prompt
# ---------------------------------------------------------------------------


def test_render_task_prompt_from_file(tmp_path):
    prompt_file = tmp_path / "task.md"
    prompt_file.write_text("Hello ${name}.")
    result = render_task_prompt(TaskConfig(name="t1", prompt_path="task.md"), tmp_path, {"name": "Alice"})
    assert result == "Hello Alice."


def test_render_task_prompt_inline():
    result = render_task_prompt(TaskConfig(name="t1", prompt="Hello ${name}."), None, {"name": "Bob"})
    assert result == "Hello Bob."


def test_render_task_prompt_forwards_resolver(tmp_path):
    (tmp_path / "task.md").write_text("Memory: ${draft_memory}")
    result = render_task_prompt(TaskConfig(name="t1", prompt_path="task.md"), tmp_path, {}, resolve_key)
    assert result == "Memory: resolved(draft_memory)"


def test_render_task_prompt_raises_when_no_source():
    with pytest.raises(FlowConfigError, match="prompt"):
        render_task_prompt(TaskConfig.model_construct(name="t1", prompt=None, prompt_path=None), None, {})


# ---------------------------------------------------------------------------
# render_memory_prompt
# ---------------------------------------------------------------------------


def test_render_memory_prompt_from_file(tmp_path):
    (tmp_path / "mem.md").write_text("List files for ${phase_name}.")
    result = render_memory_prompt(CheckpointConfig(memory_prompt_path="mem.md"), tmp_path, {"phase_name": "draft"})
    assert result == "List files for draft."


def test_render_memory_prompt_inline():
    result = render_memory_prompt(
        CheckpointConfig(memory_prompt="List files for ${phase_name}."), None, {"phase_name": "draft"}
    )
    assert result == "List files for draft."


def test_render_memory_prompt_raises_when_no_source():
    with pytest.raises(FlowConfigError, match="memory_prompt"):
        render_memory_prompt(CheckpointConfig.model_construct(memory_prompt=None, memory_prompt_path=None), None, {})


# ---------------------------------------------------------------------------
# AgenticPhase.validate_config
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config,match",
    [
        (PhaseConfig(tasks=[TaskConfig(name="t1", prompt="x")]), "requires 'agent'"),
        (PhaseConfig(agent="ghost", tasks=[TaskConfig(name="t1", prompt="x")]), "unknown agent"),
        (PhaseConfig(agent="writer"), "at least one task"),
    ],
    ids=["missing_agent", "unknown_agent", "empty_tasks"],
)
def test_validate_config_rejects_invalid(config, match):
    with pytest.raises(FlowConfigError, match=match):
        AgenticPhase.validate_config("p1", config, {"writer": AgentConfig()})


def test_validate_config_accepts_valid():
    AgenticPhase.validate_config(
        "p1", PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="x")]), {"writer": AgentConfig()}
    )


# ---------------------------------------------------------------------------
# process_message — happy path
# ---------------------------------------------------------------------------


async def test_happy_path_single_task(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([make_response("task done", 100, 50), make_response("summary", 10, 5)])
    phase, mgr = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.memory_content("p1") == "summary"
    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "success"
    assert checkpoint["tokens"] == {"total_input": 110, "total_output": 55}
    assert mock_agent.send_calls[0] == "Do the work."
    assert "Write a brief summary" in mock_agent.send_calls[1]
    # checkpoint memory_path points to the written file
    memory_path = Path(checkpoint["memory_path"])
    assert memory_path.is_absolute() and memory_path.exists() and memory_path.name == "p1_memory.md"


async def test_happy_path_two_tasks_accumulates_tokens(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent(
        [
            make_response("t1 done", 100, 50),
            make_response("t2 done", 200, 80),
            make_response("summary", 10, 5),
        ]
    )
    phase, mgr = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="First."), TaskConfig(name="t2", prompt="Second.")],
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read()["p1"]["tokens"] == {"total_input": 310, "total_output": 135}


# ---------------------------------------------------------------------------
# process_message — context compaction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("context_pct,expect_compact", [(85, True), (50, False)], ids=["above", "below"])
async def test_compact_between_tasks(flow_dir, monkeypatch, message_queue, context_pct, expect_compact):
    mock_agent = MockAgent(
        [
            make_response("t1 done", 100, 50, context_pct=context_pct),
            make_response("t2 done", 200, 80),
            make_response("summary", 10, 5),
        ]
    )
    phase, _ = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="First."), TaskConfig(name="t2", prompt="Second.")],
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert (mock_agent.compact_call_count >= 1) == expect_compact


# ---------------------------------------------------------------------------
# process_message — before_react / after_react hooks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("hook_name", ["before_react", "after_react"], ids=["before", "after"])
async def test_react_hook_failure_fails_phase(flow_dir, monkeypatch, message_queue, hook_name):
    mock_agent = MockAgent([make_response("done", 100, 50)])
    phase, mgr = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)
    setattr(phase, hook_name, lambda: (_ for _ in ()).throw(RuntimeError("hook failed")))

    with pytest.raises(RuntimeError, match="hook failed"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


# ---------------------------------------------------------------------------
# process_message — template context
# ---------------------------------------------------------------------------


async def test_flow_variables_rendered_in_system_prompt(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}")
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    captured: dict = {}
    phase, _ = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        flow_variables={"project": "myproj"},
        captured_agent_kwargs=captured,
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured["system_prompt"] == "Project: myproj"


async def test_runtime_variables_override_flow_variables(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}")
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    captured: dict = {}
    phase, _ = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        flow_variables={"project": "flow"},
        runtime_variables={"project": "runtime"},
        captured_agent_kwargs=captured,
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured["system_prompt"] == "Project: runtime"


async def test_task_prompt_resolves_memory_variable(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    phase, mgr = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        phase_id="review",
        tasks=[TaskConfig(name="t1", prompt="Review: ${draft_memory}")],
    )
    mgr.write_memory("draft", "Created file.py")

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mock_agent.send_calls[0] == "Review: Created file.py"


# ---------------------------------------------------------------------------
# process_message — failure modes
# ---------------------------------------------------------------------------


async def test_memory_api_failure_fails_phase(flow_dir, monkeypatch, message_queue):
    # Only one response — IndexError when memory step tries to call agent again
    phase, mgr = make_agent_phase(
        flow_dir, MockAgent([make_response("task done", 100, 50)]), monkeypatch, message_queue
    )

    with pytest.raises(IndexError):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


async def test_memory_template_render_failure_fails_phase(flow_dir, monkeypatch, message_queue):
    phase, mgr = make_agent_phase(
        flow_dir,
        MockAgent([make_response("task done", 100, 50)]),
        monkeypatch,
        message_queue,
        checkpoint=CheckpointConfig(memory_prompt="Summarize."),
    )
    monkeypatch.setattr(
        "ddev.ai.phases.agentic_phase.render_memory_prompt",
        lambda *a, **kw: (_ for _ in ()).throw(ValueError("bad template")),
    )

    with pytest.raises(ValueError, match="bad template"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


async def test_disk_failure_on_write_memory_fails_phase(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([make_response("task done", 100, 50), make_response("summary", 10, 5)])
    phase, mgr = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)
    monkeypatch.setattr(
        "ddev.ai.phases.checkpoint.CheckpointManager.write_memory",
        lambda *a, **kw: (_ for _ in ()).throw(PermissionError("read-only")),
    )

    with pytest.raises(PermissionError, match="read-only"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}


# ---------------------------------------------------------------------------
# AgenticPhase._run_memory_step
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "checkpoint,expected_user_additions",
    [(None, None), (CheckpointConfig(memory_prompt="anything"), "USER_ADDITIONS")],
    ids=["no_checkpoint", "with_checkpoint"],
)
async def test_run_memory_step_passes_user_additions_to_build(
    flow_dir, monkeypatch, message_queue, checkpoint, expected_user_additions
):
    mock_agent = MockAgent([make_response("ok", 0, 0)])
    phase, mgr = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue, checkpoint=checkpoint)
    monkeypatch.setattr("ddev.ai.phases.agentic_phase.render_memory_prompt", lambda *a, **kw: "USER_ADDITIONS")
    build_calls: list = []
    monkeypatch.setattr(
        mgr, "build_memory_prompt", lambda user_additions: build_calls.append(user_additions) or "PROMPT"
    )

    await phase._run_memory_step(mock_agent, {})

    assert build_calls == [expected_user_additions]


async def test_run_memory_step_sends_built_prompt_with_no_tools(flow_dir, monkeypatch, message_queue):
    captured: dict = {}

    class CapturingAgent(MockAgent):
        async def send(self, content, allowed_tools=None):
            captured.update({"content": content, "allowed_tools": allowed_tools})
            return await super().send(content, allowed_tools)

    agent = CapturingAgent([make_response("ok", 0, 0)])
    phase, mgr = make_agent_phase(flow_dir, agent, monkeypatch, message_queue)
    monkeypatch.setattr(mgr, "build_memory_prompt", lambda _: "BUILT")

    await phase._run_memory_step(agent, {})

    assert captured == {"content": "BUILT", "allowed_tools": []}


async def test_run_memory_step_returns_response_data_and_fires_callbacks(flow_dir, monkeypatch, message_queue):
    events: list = []
    cb_set = CallbackSet()

    @cb_set.on_before_agent_send
    async def _before(iteration):
        events.append(("before", iteration))

    @cb_set.on_agent_response
    async def _response(response, iteration):
        events.append(("response", iteration, response.text))

    mock_agent = MockAgent([make_response("summary text", 7, 3)])
    phase, _ = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue, callbacks=Callbacks([cb_set]))

    result = await phase._run_memory_step(mock_agent, {})

    assert result == ("summary text", 7, 3)
    assert events == [("before", 1), ("response", 1, "summary text")]


# ---------------------------------------------------------------------------
# AgenticPhase with spawn_subagent — wiring smoke test
# ---------------------------------------------------------------------------


async def test_spawn_subagent_wiring(flow_dir, message_queue):
    """Phase correctly passes subagent_builder + log_dir to the agent builder at execute time."""

    def make_usage() -> TokenUsage:
        return TokenUsage(input_tokens=100, output_tokens=50, cache_read_input_tokens=0, cache_creation_input_tokens=0)

    spawn_call = ToolCall(
        id="tc1",
        name="spawn_subagent",
        input={"system_prompt": "you are a helper", "prompt": "answer 42", "tools": [], "name": "child"},
    )
    parent_agent = MockAgent(
        [
            AgentResponse(stop_reason=StopReason.TOOL_USE, text="", tool_calls=[spawn_call], usage=make_usage()),
            AgentResponse(stop_reason=StopReason.END_TURN, text="parent done", tool_calls=[], usage=make_usage()),
            AgentResponse(stop_reason=StopReason.END_TURN, text="memory summary", tool_calls=[], usage=make_usage()),
        ]
    )

    subagent_calls: list = []

    def mock_subagent_builder(system_prompt: str, owner_id: str, tool_names: list[str]):
        subagent_calls.append(system_prompt)
        return MockAgent(
            [AgentResponse(stop_reason=StopReason.END_TURN, text="42", tool_calls=[], usage=make_usage())]
        ), ToolRegistry([])

    from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentTool

    def agent_builder_fn(system_prompt: str, owner_id: str, subagent_builder=None, log_dir=None):
        parent_agent.name = owner_id
        return parent_agent, ToolRegistry(
            [
                SpawnSubagentTool(
                    owner_id=owner_id,
                    subagent_builder=subagent_builder,
                    allowed_tools=[],
                    log_dir=log_dir,
                )
            ]
        )

    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    phase = AgenticPhase(
        phase_id="p1",
        dependencies=[],
        config=PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="Do the work.")]),
        agent_builder=agent_builder_fn,
        checkpoint_manager=checkpoint_manager,
        runtime_variables={},
        flow_variables={},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
        subagent_builder=mock_subagent_builder,
    )
    phase.queue = message_queue

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    submitted = [message_queue.get_nowait() for _ in range(message_queue.qsize())]
    assert not any(isinstance(m, PhaseFailedMessage) for m in submitted)
    assert subagent_calls == ["you are a helper"]

    log_file = checkpoint_manager.root / "subagents" / "p1" / "001-child.jsonl"
    assert log_file.exists()
    events = {e["event"] for e in read_jsonl(log_file)}
    assert {"start", "finish"} <= events
