# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ddev.ai.agent.build import AgentRuntimeFactory
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import AgentConfig, TaskConfig
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.agents.agent_logger import AgentLogger
from ddev.ai.tools.registry import filter_read_only

GOAL_REVIEWER_SYSTEM_PROMPT = """\
You are a strict, independent reviewer. Your only job is to verify whether a
goal was met by another agent. You do not fix anything; you only report.

You will receive a user message with three sections:
1. "Original task" — the prompt the worker agent was given.
2. "Goal to verify" — the specific criterion you must check.
3. "Worker summary" — the worker's own description of what it did, including
   any files it created or modified, and any intentional decisions about scope.

How to work:
- Read the relevant files yourself with the tools provided. Do not trust the
  worker summary blindly — verify it.
- If the worker summary explains that an apparent gap is intentional and the
  explanation is plausible and consistent with the task, accept that specific
  gap as valid.
- Be specific in your reasoning. Vague rejections are useless to the worker.

Output contract:
- Reply with ONLY a JSON object as your final response, with no surrounding prose
  and no markdown code fences.
- Schema: {"valid": <bool>, "reason": <string>}.
- "reason" must be specific and actionable when "valid" is false.
- "reason" may be an empty string when "valid" is true.
"""

GOAL_TASK_SUFFIX = """

---
Before you finish, write a brief summary of what you did. Include:
- the files you created or modified (with absolute paths),
- any intentional decisions about scope (e.g. items deliberately excluded and why),
- anything a reviewer would need to verify your work.
Your work will be checked by an independent reviewer using only this summary
and the files you produced.
"""

GOAL_RETRY_PROMPT_TEMPLATE = """\
A reviewer checked your work against this goal and reported it failed:

Goal: {goal}

Reviewer reason: {reason}

Address only the issue above. If you believe the reviewer is wrong, explain
why clearly in your final summary (do not silently ignore it).
"""

GOAL_PARSE_RETRY_PROMPT = (
    "Your previous reply was not a valid JSON object matching the schema "
    '{"valid": <bool>, "reason": <string>}. Reply with only that JSON object, '
    "with no surrounding prose and no markdown code fences."
)


class GoalValidationError(Exception):
    """Base class for goal-validation failures. Carries the token cost and attempt count."""

    def __init__(self, message: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.attempts: int = 0


class GoalParseError(GoalValidationError):
    """Reviewer failed to return valid JSON after the parse-retry."""


class GoalAttemptsExhausted(GoalValidationError):
    """Reviewer rejected the work on every attempt up to max_goal_attempts."""


@dataclass(frozen=True)
class GoalCheckResult:
    valid: bool
    reason: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class GoalLoopOutcome:
    final_result: ReActResult
    attempts: int
    total_input_tokens: int
    total_output_tokens: int


def render_goal_text(
    task: TaskConfig,
    config_dir: Path,
    context: dict[str, Any],
    resolver: Callable[[str], str] | None,
) -> str:
    """Render the goal — from file if goal_path is set, inline otherwise."""
    if task.goal_path is not None:
        return render_prompt(config_dir / task.goal_path, context, resolver)
    assert task.goal is not None  # caller checks
    return render_inline(task.goal, context, resolver)


def build_reviewer_user_message(
    *,
    rendered_task_prompt: str,
    goal_text: str,
    worker_summary: str,
) -> str:
    return (
        f"## Original task\n{rendered_task_prompt}\n\n"
        f"## Goal to verify\n{goal_text}\n\n"
        f"## Worker summary\n{worker_summary}\n"
    )


def parse_reviewer_output(text: str) -> tuple[bool, str] | None:
    """Return (valid, reason) if text parses; None if it does not."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        obj = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    valid = obj.get("valid")
    reason = obj.get("reason", "")
    if not isinstance(valid, bool) or not isinstance(reason, str):
        return None
    return valid, reason


async def _run_reviewer_once(
    reviewer_process: ReActProcess,
    user_message: str,
) -> GoalCheckResult:
    """Send ``user_message`` to the reviewer and parse its JSON output.

    On parse failure, ask the reviewer once more for valid JSON. If that
    second response still does not parse, raise GoalParseError.
    """
    result = await reviewer_process.start(user_message)
    in_tokens = result.total_input_tokens
    out_tokens = result.total_output_tokens

    parsed = parse_reviewer_output(result.final_response.text or "")
    if parsed is None:
        retry_result = await reviewer_process.start(GOAL_PARSE_RETRY_PROMPT)
        in_tokens += retry_result.total_input_tokens
        out_tokens += retry_result.total_output_tokens
        parsed = parse_reviewer_output(retry_result.final_response.text or "")
        if parsed is None:
            raise GoalParseError(
                "Reviewer did not return valid JSON after one parse-retry. "
                f"Last raw output: {retry_result.final_response.text!r}",
                input_tokens=in_tokens,
                output_tokens=out_tokens,
            )

    valid, reason = parsed
    return GoalCheckResult(valid=valid, reason=reason, input_tokens=in_tokens, output_tokens=out_tokens)


async def _drive_goal_loop(
    *,
    task: TaskConfig,
    goal_text: str,
    rendered_task_prompt: str,
    worker_process: ReActProcess,
    initial_result: ReActResult,
    reviewer_process: ReActProcess,
    callbacks: Callbacks,
    compact_if_needed: Callable[[ReActResult], Awaitable[tuple[int, int]]],
) -> GoalLoopOutcome:
    total_in = total_out = 0
    attempts = 0
    worker_result = initial_result

    try:
        while True:
            attempts += 1
            await callbacks.fire_before_goal_check(task.name, attempts)

            user_message = build_reviewer_user_message(
                rendered_task_prompt=rendered_task_prompt,
                goal_text=goal_text,
                worker_summary=worker_result.final_response.text or "(no summary provided)",
            )

            if attempts > 1:
                reviewer_process.reset()

            check = await _run_reviewer_once(reviewer_process, user_message)
            total_in += check.input_tokens
            total_out += check.output_tokens

            await callbacks.fire_after_goal_check(task.name, attempts, check.valid, check.reason)

            if check.valid:
                return GoalLoopOutcome(
                    final_result=worker_result,
                    attempts=attempts,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                )

            if attempts >= task.max_goal_attempts:
                raise GoalAttemptsExhausted(
                    f"Task {task.name!r} failed goal validation after "
                    f"{attempts} attempts. Last reviewer reason: {check.reason}"
                )

            compact_in, compact_out = await compact_if_needed(worker_result)
            total_in += compact_in
            total_out += compact_out

            retry_prompt = GOAL_RETRY_PROMPT_TEMPLATE.format(goal=goal_text, reason=check.reason)
            worker_result = await worker_process.start(retry_prompt)
            total_in += worker_result.total_input_tokens
            total_out += worker_result.total_output_tokens
    except GoalValidationError as e:
        e.input_tokens += total_in
        e.output_tokens += total_out
        e.attempts = attempts
        raise


async def run_goal_loop(
    *,
    task: TaskConfig,
    goal_text: str,
    rendered_task_prompt: str,
    worker_process: ReActProcess,
    initial_result: ReActResult,
    parent_agent_config: AgentConfig,
    runtime_factory: AgentRuntimeFactory,
    callbacks: Callbacks,
    phase_id: str,
    log_root: Path,
    compact_if_needed: Callable[[ReActResult], Awaitable[tuple[int, int]]],
) -> GoalLoopOutcome:
    """Drive the reviewer + worker-retry loop for a single task with a goal.

    Reviewer activity is logged to ``<log_root>/goal_agent/<phase_id>/<task_name>.jsonl``
    via AgentLogger. The reviewer's ReActProcess uses only the logger's callbacks —
    the phase callbacks see only the bracketing before/after_goal_check events.
    """
    log_dir = log_root / "goal_agent" / phase_id
    log_path = log_dir / f"{task.name}.jsonl"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Goal reviewer log directory could not be created at {log_dir}: {e}") from e

    reviewer_owner_id = f"{phase_id}.goal.{task.name}"
    reviewer_config = AgentConfig(
        provider=parent_agent_config.provider,
        tools=filter_read_only(parent_agent_config.tools),
    )
    reviewer_runtime = runtime_factory.build_runtime(
        agent_config=reviewer_config,
        system_prompt=GOAL_REVIEWER_SYSTEM_PROMPT,
        owner_id=reviewer_owner_id,
    )

    try:
        agent_logger = AgentLogger(log_path)
    except OSError as e:
        raise OSError(f"Goal reviewer log could not be opened at {log_path}: {e}") from e

    try:
        agent_logger.log_start(
            system_prompt=GOAL_REVIEWER_SYSTEM_PROMPT,
            prompt=f"<goal loop for task {task.name!r}>",
            tools=[d["name"] for d in reviewer_runtime.tool_registry.definitions],
        )
        reviewer_process = ReActProcess(
            reviewer_runtime,
            callbacks=agent_logger.build_callbacks(),
        )

        outcome = await _drive_goal_loop(
            task=task,
            goal_text=goal_text,
            rendered_task_prompt=rendered_task_prompt,
            worker_process=worker_process,
            initial_result=initial_result,
            reviewer_process=reviewer_process,
            callbacks=callbacks,
            compact_if_needed=compact_if_needed,
        )
        agent_logger.log_finish(
            success=True,
            attempts=outcome.attempts,
            total_input_tokens=outcome.total_input_tokens,
            total_output_tokens=outcome.total_output_tokens,
        )
        return outcome
    except GoalValidationError as e:
        agent_logger.log_finish(
            success=False,
            attempts=e.attempts,
            total_input_tokens=e.input_tokens,
            total_output_tokens=e.output_tokens,
            error=f"{type(e).__name__}: {e}",
        )
        raise
    finally:
        agent_logger.close()
