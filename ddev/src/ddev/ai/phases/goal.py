# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig, TaskConfig
from ddev.ai.phases.messages import TaskValidationStatus
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.registry import filter_read_only

GOAL_REVIEWER_RESET_THRESHOLD_PCT = 75.0

GOAL_REVIEWER_SYSTEM_PROMPT = """\
You are a strict, independent reviewer. Your only job is to verify whether a
goal was met by another agent. You do not fix anything; you only report.

The initial user message has three sections:
1. "Original task" — the prompt the worker agent was given.
2. "Goal to verify" — the specific criterion you must check.
3. "Worker summary" — the worker's own description of what it did, including
   any files it created or modified, and any intentional decisions about scope.

How to work:
- Read the relevant files yourself with the tools provided. Do not trust the
  worker summary blindly — verify it.
- On the initial review, inspect the complete goal and report all findings you
  discover so the worker can repair them together.
- On a repair review, verify the previous findings against the worker's repair
  summary and inspect only the files and directly affected invariants involved
  in that repair. When your prior conversation is available, preserve its
  conclusions about everything else. When the message includes a previous
  verdict, use it as the source of those conclusions because your context was
  cleared. Perform a full review only if the repair was broad enough to affect
  unrelated criteria.
- If the worker summary explains that an apparent gap is intentional and the
  explanation is plausible and consistent with the task, accept that specific
  gap as valid.
- Be specific in your reasoning. Vague rejections are useless to the worker.

Output contract:
- End your reply with the verdict as a single-line JSON object on the LAST line,
  with nothing after it.
- That final line must be valid JSON on one line, with no markdown code fences
  and not split across multiple lines.
- Schema: {"valid": <bool>, "reason": <string>, "findings": <array>}.
- "reason" must be specific and actionable when "valid" is false.
- "reason" may be an empty string when "valid" is true.
- "findings" must contain every discovered problem. Each entry must be an
  object with a stable string "id", a string "criterion", and a string "reason".
  Return at least one finding when the goal is invalid and an empty array when
  the goal is valid.
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

VALIDATION_RETRY_PROMPT_TEMPLATE = """\
A validation check found that your work is incomplete.{goal_section}

Validation reason: {reason}

Address only the issue above. If you believe the validation is wrong, explain
why clearly in your final summary (do not silently ignore it).
"""

REVIEWER_RETRY_PROMPT_TEMPLATE = """\
A reviewer checked your work against this goal and reported it failed:

Goal: {goal}

Reviewer verdict: {reviewer_verdict}

Address all findings above and avoid unrelated changes. If you believe the
reviewer is wrong, explain why clearly in your final summary (do not silently
ignore it). Finish with a precise repair summary that lists:
- every file you changed,
- what you changed in each file,
- which finding ID each change addresses,
- any additional changes and why they were necessary.
"""

GOAL_PARSE_RETRY_PROMPT = (
    "Your previous reply did not end with a valid JSON verdict. End your reply with a "
    'single-line JSON object as the LAST line: {"valid": <bool>, "reason": <string>, '
    '"findings": <array>}, with no markdown code fences and nothing after it. Each finding '
    'must be an object with a stable string "id", a string "criterion", and a string "reason". '
    'Return at least one finding when "valid" is false and an empty array when "valid" is true.'
)


class TaskValidationError(Exception):
    """Base class for task-validation failures. Carries the token cost and attempt count."""

    def __init__(self, message: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.attempts: int = 0


class ReviewerParseError(TaskValidationError):
    """Reviewer failed to return valid JSON after the parse-retry."""


class ValidationAttemptsExhausted(TaskValidationError):
    """Validation rejected every candidate up to max_validation_attempts."""


class ReviewerProcessError(TaskValidationError):
    """The lazy goal-reviewer process could not be created."""


@dataclass(frozen=True)
class ReviewerCheckResult:
    valid: bool
    reason: str
    input_tokens: int
    output_tokens: int
    verdict_json: str
    context_pct: float | None


@dataclass(frozen=True)
class ValidationLoopOutcome:
    final_result: ReActResult
    attempts: int
    total_input_tokens: int
    total_output_tokens: int


@dataclass(frozen=True)
class DeterministicCheck:
    """A named, repeatable artifact check that does not require a model reviewer."""

    name: str
    run: Callable[[], str | None]


@dataclass(frozen=True)
class DeterministicCheckFailure:
    """A repairable failure returned by one deterministic check."""

    name: str
    reason: str


@dataclass(frozen=True)
class DeterministicCheckReport:
    """The ordered composition of every failure from one deterministic pass."""

    failures: tuple[DeterministicCheckFailure, ...]

    @property
    def valid(self) -> bool:
        return not self.failures

    def failure_reason(self) -> str | None:
        """Render every failure in declaration order, or ``None`` when all checks passed."""
        if self.valid:
            return None
        sections = [f"## {failure.name}\n{failure.reason}" for failure in self.failures]
        return "Deterministic checks failed:\n\n" + "\n\n".join(sections)


def validate_check_names(checks: Sequence[DeterministicCheck]) -> None:
    """Validate that check names are non-blank and unique.

    Raises ValueError if any check name is blank or duplicated.
    """
    names = [check.name.strip() for check in checks]
    if invalid_names := [check.name for check, name in zip(checks, names, strict=True) if not name]:
        raise ValueError(f"Deterministic check names must not be blank: {invalid_names!r}")
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        raise ValueError(f"Deterministic check names must be unique: {duplicates}")


def run_deterministic_checks(checks: Sequence[DeterministicCheck]) -> DeterministicCheckReport:
    """Run every named deterministic check and compose all repairable failures."""
    validate_check_names(checks)

    failures: list[DeterministicCheckFailure] = []
    for check in checks:
        name = check.name.strip()
        reason = check.run()
        if reason is None:
            continue
        if not reason.strip():
            raise ValueError(f"Deterministic check {name!r} returned a blank failure reason")
        failures.append(DeterministicCheckFailure(name=name, reason=reason))
    return DeterministicCheckReport(failures=tuple(failures))


def build_validation_retry_prompt(goal_text: str | None, reason: str) -> str:
    """Build worker feedback for a deterministic-check failure."""
    goal_section = f"\n\nGoal: {goal_text}" if goal_text is not None else ""
    return VALIDATION_RETRY_PROMPT_TEMPLATE.format(goal_section=goal_section, reason=reason)


def build_reviewer_retry_prompt(goal_text: str, reviewer_verdict: str) -> str:
    """Build worker feedback for a reviewer-rejected goal, including its findings."""
    return REVIEWER_RETRY_PROMPT_TEMPLATE.format(goal=goal_text, reviewer_verdict=reviewer_verdict)


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


def build_reviewer_retry_message(
    *,
    worker_summary: str,
) -> str:
    return (
        "## Re-review instructions\n"
        "Confirm every previous finding is resolved. Inspect only the files and directly affected "
        "invariants identified by the worker's repair summary. Preserve your previous conclusions "
        "about everything else. Perform a full review only if the reported repair is broad enough "
        "to affect unrelated goal criteria.\n\n"
        f"## Worker repair summary\n{worker_summary}\n"
    )


def build_reviewer_reset_retry_message(
    *,
    rendered_task_prompt: str,
    goal_text: str,
    previous_verdict: str,
    worker_summary: str,
) -> str:
    return (
        "## Re-review instructions\n"
        "This work was already reviewed, but your previous conversation was cleared to free "
        "context. Treat the previous verdict below as the established review state. Confirm every "
        "finding is resolved, inspecting only the repaired files and directly affected invariants. "
        "Perform a full review only if the repair was broad enough to affect unrelated goal "
        "criteria.\n\n"
        f"## Original task\n{rendered_task_prompt}\n\n"
        f"## Goal to verify\n{goal_text}\n\n"
        f"## Previous reviewer verdict\n{previous_verdict}\n\n"
        f"## Worker repair summary\n{worker_summary}\n"
    )


def _select_reviewer_message(
    *,
    previous_check: ReviewerCheckResult | None,
    rendered_task_prompt: str,
    goal_text: str,
    worker_summary: str,
) -> tuple[str, bool]:
    if previous_check is None:
        return (
            build_reviewer_user_message(
                rendered_task_prompt=rendered_task_prompt,
                goal_text=goal_text,
                worker_summary=worker_summary,
            ),
            False,
        )

    needs_reset = (
        previous_check.context_pct is not None and previous_check.context_pct >= GOAL_REVIEWER_RESET_THRESHOLD_PCT
    )
    if needs_reset:
        return (
            build_reviewer_reset_retry_message(
                rendered_task_prompt=rendered_task_prompt,
                goal_text=goal_text,
                previous_verdict=previous_check.verdict_json,
                worker_summary=worker_summary,
            ),
            True,
        )

    return build_reviewer_retry_message(worker_summary=worker_summary), False


def _parse_verdict_object(candidate: str) -> dict[str, object] | None:
    """Parse and validate the reviewer verdict object.

    Example::

        {
            "valid": false,
            "reason": "The metrics mapping is incomplete.",
            "findings": [
                {
                    "id": "missing-metric",
                    "criterion": "mapping-composition",
                    "reason": "requests_total is absent from metrics.yaml."
                }
            ]
        }
    """
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
    reason = obj.get("reason")
    if not isinstance(valid, bool) or not isinstance(reason, str):
        return None
    findings = obj.get("findings")
    if not isinstance(findings, list):
        return None
    for finding in findings:
        if not isinstance(finding, dict):
            return None
        if not all(isinstance(finding.get(key), str) for key in ("id", "criterion", "reason")):
            return None
    if valid == bool(findings):
        return None
    return obj


def parse_reviewer_verdict(text: str) -> dict[str, object] | None:
    """Return the complete validated verdict object from reviewer output."""
    candidates: list[str] = []
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if non_empty_lines:
        candidates.append(non_empty_lines[-1])
    whole = text.strip()
    if whole and whole not in candidates:
        candidates.append(whole)
    for candidate in candidates:
        parsed = _parse_verdict_object(candidate)
        if parsed is not None:
            return parsed
    return None


async def _run_reviewer_once(
    reviewer_process: ReActProcess,
    user_message: str,
) -> ReviewerCheckResult:
    """Send ``user_message`` to the reviewer and parse its JSON output.

    On parse failure, ask the reviewer once more for valid JSON. If that
    second response still does not parse, raise ReviewerParseError.
    """
    result = await reviewer_process.start(user_message)
    in_tokens = result.total_input_tokens
    out_tokens = result.total_output_tokens
    context_usage = result.context_usage

    raw_output = result.final_response.text or ""
    parsed = parse_reviewer_verdict(raw_output)
    if parsed is None:
        retry_result = await reviewer_process.start(GOAL_PARSE_RETRY_PROMPT)
        in_tokens += retry_result.total_input_tokens
        out_tokens += retry_result.total_output_tokens
        context_usage = retry_result.context_usage
        raw_output = retry_result.final_response.text or ""
        parsed = parse_reviewer_verdict(raw_output)
        if parsed is None:
            raise ReviewerParseError(
                "Reviewer did not return valid JSON after one parse-retry. "
                f"Last raw output: {retry_result.final_response.text!r}",
                input_tokens=in_tokens,
                output_tokens=out_tokens,
            )

    return ReviewerCheckResult(
        valid=bool(parsed["valid"]),
        reason=str(parsed.get("reason", "")),
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        verdict_json=json.dumps(parsed, sort_keys=True),
        context_pct=context_usage.context_pct if context_usage is not None else None,
    )


def build_reviewer_process(
    *,
    task: TaskConfig,
    parent_agent_config: AgentConfig,
    process_factory: ReActProcessFactory,
    phase_id: str,
) -> ReActProcess:
    """Create the lazy goal-reviewer process for one task."""
    reviewer_scope = AgentScope(
        owner_id=f"{phase_id}.goal.{task.name}",
        role=AgentRole.GOAL_REVIEWER,
        phase_id=phase_id,
    )
    reviewer_config = parent_agent_config.model_copy(update={"tools": filter_read_only(parent_agent_config.tools)})
    try:
        return process_factory.create(
            scope=reviewer_scope,
            agent_config=reviewer_config,
            system_prompt=GOAL_REVIEWER_SYSTEM_PROMPT,
        )
    except Exception as e:
        raise ReviewerProcessError(f"Failed to create reviewer process for task {task.name}: {e}") from e


async def run_validation_loop(
    *,
    task: TaskConfig,
    goal_text: str | None,
    rendered_task_prompt: str,
    worker_process: ReActProcess,
    initial_result: ReActResult,
    parent_agent_config: AgentConfig,
    process_factory: ReActProcessFactory,
    callbacks: Callbacks,
    phase_id: str,
    compact_if_needed: Callable[[ReActResult], Awaitable[tuple[int, int]]],
    deterministic_checks: Sequence[DeterministicCheck] = (),
) -> ValidationLoopOutcome:
    """Validate and repair a task with deterministic checks, an optional reviewer, or both."""
    total_in = total_out = 0
    attempts = 0
    worker_result = initial_result
    reviewer_process: ReActProcess | None = None
    previous_check: ReviewerCheckResult | None = None

    async def _succeed() -> ValidationLoopOutcome:
        await callbacks.fire_after_task_validation(
            phase_id,
            task.name,
            attempts,
            TaskValidationStatus.PASSED,
            "",
        )
        return ValidationLoopOutcome(
            final_result=worker_result,
            attempts=attempts,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
        )

    try:
        while True:
            attempts += 1
            await callbacks.fire_before_task_validation(phase_id, task.name, attempts)
            failure_reason = run_deterministic_checks(deterministic_checks).failure_reason()
            reviewer_feedback: tuple[str, str] | None = None

            if failure_reason is None:
                if goal_text is None:
                    return await _succeed()
                if reviewer_process is None:
                    reviewer_process = build_reviewer_process(
                        task=task,
                        parent_agent_config=parent_agent_config,
                        process_factory=process_factory,
                        phase_id=phase_id,
                    )

                worker_summary = worker_result.final_response.text or "(no summary provided)"
                user_message, needs_reset = _select_reviewer_message(
                    previous_check=previous_check,
                    rendered_task_prompt=rendered_task_prompt,
                    goal_text=goal_text,
                    worker_summary=worker_summary,
                )
                if needs_reset:
                    await reviewer_process.reset()

                reviewer_result = await _run_reviewer_once(reviewer_process, user_message)
                previous_check = reviewer_result
                total_in += reviewer_result.input_tokens
                total_out += reviewer_result.output_tokens
                if reviewer_result.valid:
                    return await _succeed()
                failure_reason = reviewer_result.reason
                reviewer_feedback = (goal_text, reviewer_result.verdict_json)

            validation_status = (
                TaskValidationStatus.RETRYING
                if attempts < task.max_validation_attempts
                else TaskValidationStatus.FAILED
            )
            await callbacks.fire_after_task_validation(
                phase_id,
                task.name,
                attempts,
                validation_status,
                failure_reason,
            )
            if validation_status is TaskValidationStatus.FAILED:
                raise ValidationAttemptsExhausted(
                    f"Task {task.name!r} failed validation after "
                    f"{attempts} attempts. Last validation reason: {failure_reason}"
                )

            compact_in, compact_out = await compact_if_needed(worker_result)
            total_in += compact_in
            total_out += compact_out

            retry_prompt = (
                build_reviewer_retry_prompt(*reviewer_feedback)
                if reviewer_feedback is not None
                else build_validation_retry_prompt(goal_text, failure_reason)
            )
            worker_result = await worker_process.start(retry_prompt)
            total_in += worker_result.total_input_tokens
            total_out += worker_result.total_output_tokens
    except TaskValidationError as e:
        e.input_tokens += total_in
        e.output_tokens += total_out
        e.attempts = attempts
        raise
