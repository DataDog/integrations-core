# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig, TaskConfig
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
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
- End your reply with the verdict as a single-line JSON object on the LAST line,
  with nothing after it.
- That final line must be valid JSON on one line, with no markdown code fences
  and not split across multiple lines.
- Schema: {"valid": <bool>, "reason": <string>}.
- "reason" must be specific and actionable when "valid" is false.
- "reason" may be an empty string when "valid" is true.
- You may write your reasoning as prose before that final line; only the last
  line is read as the verdict.
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
    "Your previous reply did not end with a valid JSON verdict. End your reply with a "
    'single-line JSON object as the LAST line: {"valid": <bool>, "reason": <string>}, '
    "with no markdown code fences and nothing after it."
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


def _parse_verdict(candidate: str) -> tuple[bool, str] | None:
    """Parse a single candidate string into (valid, reason); None if it does not match the schema."""
    stripped = candidate.strip()
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


def parse_reviewer_output(text: str) -> tuple[bool, str] | None:
    """Return (valid, reason) from the reviewer's verdict; None if it does not parse.

    The reviewer is instructed to emit the verdict as a single-line JSON object on the
    last line of its reply, so we parse that last non-empty line first and ignore any
    preceding prose. As a fallback we also try the whole reply, which covers a reviewer
    that returns only the JSON object (possibly pretty-printed across several lines).
    """
    candidates: list[str] = []
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if non_empty_lines:
        candidates.append(non_empty_lines[-1])
    whole = text.strip()
    if whole and whole not in candidates:
        candidates.append(whole)
    for candidate in candidates:
        parsed = _parse_verdict(candidate)
        if parsed is not None:
            return parsed
    return None


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
    phase_id: str,
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
            await callbacks.fire_before_goal_check(phase_id, task.name, attempts)

            user_message = build_reviewer_user_message(
                rendered_task_prompt=rendered_task_prompt,
                goal_text=goal_text,
                worker_summary=worker_result.final_response.text or "(no summary provided)",
            )

            if attempts > 1:
                await reviewer_process.reset()

            check = await _run_reviewer_once(reviewer_process, user_message)
            total_in += check.input_tokens
            total_out += check.output_tokens

            await callbacks.fire_after_goal_check(phase_id, task.name, attempts, check.valid, check.reason)

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
    process_factory: ReActProcessFactory,
    callbacks: Callbacks,
    phase_id: str,
    compact_if_needed: Callable[[ReActResult], Awaitable[tuple[int, int]]],
) -> GoalLoopOutcome:
    """Drive the reviewer + worker-retry loop for a single task with a goal.

    The reviewer runs as a scoped ``GOAL_REVIEWER`` process; its per-run activity
    is captured by the run-wide logging callbacks bound to ``process_factory``.
    The phase callbacks see only the bracketing before/after_goal_check events.
    """
    reviewer_scope = AgentScope(
        owner_id=f"{phase_id}.goal.{task.name}",
        role=AgentRole.GOAL_REVIEWER,
        phase_id=phase_id,
    )
    reviewer_config = parent_agent_config.model_copy(update={"tools": filter_read_only(parent_agent_config.tools)})
    try:
        reviewer_process = process_factory.create(
            scope=reviewer_scope,
            agent_config=reviewer_config,
            system_prompt=GOAL_REVIEWER_SYSTEM_PROMPT,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create reviewer process for task {task.name}: {e}") from e

    return await _drive_goal_loop(
        phase_id=phase_id,
        task=task,
        goal_text=goal_text,
        rendered_task_prompt=rendered_task_prompt,
        worker_process=worker_process,
        initial_result=initial_result,
        reviewer_process=reviewer_process,
        callbacks=callbacks,
        compact_if_needed=compact_if_needed,
    )
