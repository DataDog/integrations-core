# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.agentic_phase import AgenticPhase, render_memory_prompt, render_task_prompt
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.react.process import ReActProcess
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.registry import ToolRegistry

from .conftest import MockAgent, make_agent_phase, make_response, resolve_key


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _memory_process(agent: MockAgent, callbacks: Callbacks | None = None) -> ReActProcess:
    """Wrap a mock agent in a ReActProcess for direct _run_memory_step tests."""
    return ReActProcess(
        AgentRuntime(agent=agent, tool_registry=ToolRegistry([])),
        callbacks=callbacks,
        scope=AgentScope(owner_id="p1", role=AgentRole.PHASE),
    )


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


async def test_build_runtime_receives_rendered_flow_context(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}", encoding="utf-8")
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    captured: dict = {}
    phase, _ = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        flow_variables={"project": "myproj"},
        captured_worker_kwargs=captured,
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured["owner_id"] == "p1"
    assert captured["system_prompt"] == "Project: myproj"
    assert captured["agent_config"] == AgentConfig(tools=[])


async def test_build_runtime_receives_runtime_overrides(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Project: ${project}", encoding="utf-8")
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    captured: dict = {}
    phase, _ = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        flow_variables={"project": "flow"},
        runtime_variables={"project": "runtime"},
        captured_worker_kwargs=captured,
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured["system_prompt"] == "Project: runtime"


async def test_build_runtime_receives_memory_resolver(flow_dir, monkeypatch, message_queue):
    (flow_dir / "prompts" / "writer.md").write_text("Memory: ${draft_memory}", encoding="utf-8")
    mock_agent = MockAgent([make_response("done", 100, 50), make_response("summary", 10, 5)])
    captured: dict = {}
    phase, mgr = make_agent_phase(
        flow_dir,
        mock_agent,
        monkeypatch,
        message_queue,
        captured_worker_kwargs=captured,
    )
    mgr.write_memory("draft", "Created file.py")

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert captured["system_prompt"] == "Memory: Created file.py"


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
        "ddev.ai.runtime.checkpoints.CheckpointManager.write_memory",
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

    await phase._run_memory_step(_memory_process(mock_agent), {})

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

    await phase._run_memory_step(_memory_process(agent), {})

    assert captured == {"content": "BUILT", "allowed_tools": []}


async def test_run_memory_step_returns_response_data(flow_dir, monkeypatch, message_queue):
    mock_agent = MockAgent([make_response("summary text", 7, 3)])
    phase, _ = make_agent_phase(flow_dir, mock_agent, monkeypatch, message_queue)

    result = await phase._run_memory_step(_memory_process(mock_agent), {})

    assert result == ("summary text", 7, 3)


# ---------------------------------------------------------------------------
# AgenticPhase with spawn_subagent — wiring smoke test
# ---------------------------------------------------------------------------


async def test_spawn_subagent_wiring(flow_context, monkeypatch, message_queue):
    """Real runtime factory wires spawn_subagent logs under the checkpoint root."""
    flow_dir = flow_context.config_dir

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
    subagent = MockAgent([AgentResponse(stop_reason=StopReason.END_TURN, text="42", tool_calls=[], usage=make_usage())])

    agents = [parent_agent, subagent]

    def fake_anthropic_agent(*, tools, system_prompt, name, **kwargs):
        agent = agents.pop(0)
        agent.name = name
        agent._system_prompt = system_prompt
        return agent

    monkeypatch.setattr("ddev.ai.agent.build.AnthropicAgent", fake_anthropic_agent)

    from ddev.ai.runtime.resources import RunResources

    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    run_callbacks = Callbacks([AgentLogger(checkpoint_manager.root).as_callback_set()])
    resources = RunResources(
        agent_clients={"anthropic": object()},
        file_access_policy=FileAccessPolicy(write_root=flow_dir),
        agents={"writer": AgentConfig(tools=["spawn_subagent"])},
        callbacks=run_callbacks,
    )
    phase = AgenticPhase.build(
        phase_id="p1",
        config=PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="Do the work.")]),
        deps=[],
        resources=resources,
        checkpoint_manager=checkpoint_manager,
        context=flow_context,
    )
    phase.queue = message_queue

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    submitted = [message_queue.get_nowait() for _ in range(message_queue.qsize())]
    assert not any(isinstance(m, PhaseFailedMessage) for m in submitted)
    assert subagent._system_prompt == "you are a helper"

    log_file = checkpoint_manager.root / "subagent" / "p1.sub.001-child.jsonl"
    assert log_file.exists()
    events = {e["event"] for e in read_jsonl(log_file)}
    assert {"start", "finish"} <= events


# ---------------------------------------------------------------------------
# Goal validation integration tests
# ---------------------------------------------------------------------------


async def test_phase_with_goal_passes_first_attempt(flow_dir, monkeypatch, message_queue):
    worker = MockAgent(
        [
            make_response("worker did the work", 100, 50),
            make_response("phase summary", 10, 5),
        ]
    )
    reviewer_responses = [make_response('{"valid": true, "reason": ""}', 7, 3)]

    captured_builder_calls: list = []

    def goal_builder(owner_id: str) -> AgentRuntime:
        captured_builder_calls.append(owner_id)
        agent = MockAgent(list(reviewer_responses))
        return AgentRuntime(agent=agent, tool_registry=ToolRegistry([]))

    phase, mgr = make_agent_phase(
        flow_dir,
        worker,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="Do it.", goal="verify it")],
        goal_runtime_builder=goal_builder,
    )

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    cp = mgr.read()["p1"]
    assert cp["status"] == "success"
    assert cp["goal_validations"] == [{"task": "t1", "attempts": 1, "final_valid": True}]
    assert worker.send_calls[0].startswith("Do it.")
    assert "independent reviewer" in worker.send_calls[0]
    assert cp["tokens"] == {"total_input": 100 + 7 + 10, "total_output": 50 + 3 + 5}
    assert captured_builder_calls == ["p1.goal.t1"]

    log_file = mgr.root / "goal_reviewer" / "p1.goal.t1.jsonl"
    assert log_file.exists()
    events = {e["event"] for e in read_jsonl(log_file)}
    assert {"start", "finish"} <= events


async def test_phase_with_goal_exhausts_attempts_fails_phase(flow_dir, monkeypatch, message_queue):
    worker = MockAgent(
        [
            make_response("attempt 1", 0, 0),
            make_response("attempt 2", 0, 0),
        ]
    )

    def goal_builder(owner_id: str) -> AgentRuntime:
        agent = MockAgent(
            [
                make_response('{"valid": false, "reason": "first miss"}', 0, 0),
                make_response('{"valid": false, "reason": "second miss"}', 0, 0),
            ]
        )
        return AgentRuntime(agent=agent, tool_registry=ToolRegistry([]))

    phase, mgr = make_agent_phase(
        flow_dir,
        worker,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="Do it.", goal="g", max_goal_attempts=2)],
        goal_runtime_builder=goal_builder,
    )

    from ddev.ai.phases.goal import GoalAttemptsExhausted

    with pytest.raises(GoalAttemptsExhausted):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}
    assert phase._goal_attempt_log == [{"task": "t1", "attempts": 2, "final_valid": False}]

    # The reviewer ran (and succeeded as an agent) on each attempt; its per-run
    # log exists. The goal-loop verdict itself lives in the phase checkpoint.
    log_file = mgr.root / "goal_reviewer" / "p1.goal.t1.jsonl"
    assert log_file.exists()
    assert "start" in {e["event"] for e in read_jsonl(log_file)}


async def test_phase_goal_partial_progress_preserved_on_exhaustion(flow_dir, monkeypatch, message_queue):
    """When task 1 passes goal validation and task 2 exhausts attempts, both entries are logged."""
    worker = MockAgent(
        [
            make_response("t1 done", 0, 0),
            make_response("t2 attempt 1", 0, 0),
            make_response("t2 attempt 2", 0, 0),
        ]
    )

    call_count = 0

    def goal_builder(owner_id: str) -> AgentRuntime:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            agent = MockAgent([make_response('{"valid": true, "reason": ""}', 0, 0)])
        else:
            agent = MockAgent(
                [
                    make_response('{"valid": false, "reason": "miss 1"}', 0, 0),
                    make_response('{"valid": false, "reason": "miss 2"}', 0, 0),
                ]
            )
        return AgentRuntime(agent=agent, tool_registry=ToolRegistry([]))

    phase, _ = make_agent_phase(
        flow_dir,
        worker,
        monkeypatch,
        message_queue,
        tasks=[
            TaskConfig(name="t1", prompt="First.", goal="check t1", max_goal_attempts=2),
            TaskConfig(name="t2", prompt="Second.", goal="check t2", max_goal_attempts=2),
        ],
        goal_runtime_builder=goal_builder,
    )

    from ddev.ai.phases.goal import GoalAttemptsExhausted

    with pytest.raises(GoalAttemptsExhausted):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert phase._goal_attempt_log == [
        {"task": "t1", "attempts": 1, "final_valid": True},
        {"task": "t2", "attempts": 2, "final_valid": False},
    ]


async def test_goal_exhaustion_tokens_captured_on_phase(flow_dir, monkeypatch, message_queue):
    """Goal-loop tokens are folded into the phase total even when the phase fails."""
    worker = MockAgent(
        [
            make_response("worker attempt 1", 10, 5),
            make_response("worker attempt 2", 10, 5),
        ]
    )

    def goal_builder(owner_id: str) -> AgentRuntime:
        return AgentRuntime(
            agent=MockAgent(
                [
                    make_response('{"valid": false, "reason": "miss 1"}', 8, 4),
                    make_response('{"valid": false, "reason": "miss 2"}', 8, 4),
                ]
            ),
            tool_registry=ToolRegistry([]),
        )

    phase, _ = make_agent_phase(
        flow_dir,
        worker,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="Do it.", goal="g", max_goal_attempts=2)],
        goal_runtime_builder=goal_builder,
    )

    from ddev.ai.phases.goal import GoalAttemptsExhausted

    with pytest.raises(GoalAttemptsExhausted):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert phase._total_input_tokens == 10 + 8 + 10 + 8
    assert phase._total_output_tokens == 5 + 4 + 5 + 4


async def test_on_error_writes_tokens_and_goal_validations_to_checkpoint(flow_dir, monkeypatch, message_queue):
    """on_error includes token counts and goal_validations in the failure checkpoint."""
    from ddev.ai.phases.messages import PhaseTrigger
    from ddev.event_bus.exceptions import MessageProcessingError

    worker = MockAgent([make_response("done", 0, 0)])
    phase, mgr = make_agent_phase(flow_dir, worker, monkeypatch, message_queue)

    phase._total_input_tokens = 42
    phase._total_output_tokens = 17
    phase._goal_attempt_log = [{"task": "t1", "attempts": 2, "final_valid": False}]
    phase._started_at = None

    err = MessageProcessingError(
        processor_name="p1",
        message=PhaseTrigger(id="start", phase_id=None),
        original_exception=RuntimeError("something went wrong"),
    )
    await phase.on_error(err)

    cp = mgr.read()["p1"]
    assert cp["status"] == "failed"
    assert cp["tokens"] == {"total_input": 42, "total_output": 17}
    assert cp["goal_validations"] == [{"task": "t1", "attempts": 2, "final_valid": False}]
    assert cp["error"] == "something went wrong"


async def test_goal_parse_error_logged_and_tokens_captured(flow_dir, monkeypatch, message_queue):
    """GoalParseError is treated the same as GoalAttemptsExhausted: logged with final_valid=False."""
    from ddev.ai.phases.goal import GoalParseError

    worker = MockAgent([make_response("worker done", 10, 5)])

    def goal_builder(owner_id: str) -> AgentRuntime:
        return AgentRuntime(
            agent=MockAgent(
                [
                    make_response("not json", 8, 4),
                    make_response("still not json", 6, 3),
                ]
            ),
            tool_registry=ToolRegistry([]),
        )

    phase, _ = make_agent_phase(
        flow_dir,
        worker,
        monkeypatch,
        message_queue,
        tasks=[TaskConfig(name="t1", prompt="Do it.", goal="g")],
        goal_runtime_builder=goal_builder,
    )

    with pytest.raises(GoalParseError):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert phase._goal_attempt_log == [{"task": "t1", "attempts": 1, "final_valid": False}]
    assert phase._total_input_tokens == 10 + 8 + 6
    assert phase._total_output_tokens == 5 + 4 + 3
