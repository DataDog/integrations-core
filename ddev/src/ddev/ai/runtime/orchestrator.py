# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import ResolvedFlow, RuntimeVariables
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager, PhaseCheckpoint, resolve_resume_state
from ddev.ai.runtime.outcome import (
    RunOutcome,
    RunOutcomeBuildError,
    RunOutcomeError,
    RunOutcomePersistenceError,
    RunOutcomeStore,
    RunSummaryMetadata,
    RunSummaryStatus,
    build_run_outcome,
)
from ddev.ai.runtime.resources import RunResources
from ddev.ai.runtime.summary import RunSummarizer, RunSummarizerLike, RunSummaryAttempt
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError, OrchestratorHookError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator

DEFAULT_GRACE_PERIOD = 10.0


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        resolved_flow: ResolvedFlow,
        phase_registry: PhaseRegistry,
        checkpoint_path: Path,
        runtime_variables: RuntimeVariables,
        provider_registry: AgentProviderRegistry,
        file_access_policy: FileAccessPolicy,
        callbacks: Callbacks | None = None,
        resume: bool = False,
        grace_period: float = DEFAULT_GRACE_PERIOD,
        logger: logging.Logger | None = None,
        summarizer_factory: Callable[[], RunSummarizerLike] | None = None,
    ) -> None:
        """Initialize the orchestrator.

        ``resolved_flow`` is a fully validated, reference-inlined flow obtained from
        ``engine.get_flow(name)``. ``phase_registry`` is the same registry the engine
        validated against, used to instantiate phase classes.

        ``provider_registry`` is the same configured registry used to validate agent
        definitions and constructs provider-specific agents on demand.

        ``file_access_policy`` must have ``write_root`` set to the integration
        output directory so that agent writes are confined to that path.

        ``summarizer_factory``, when provided, replaces the default ``RunSummarizer``
        construction (intended for tests that need to inject a fake summarizer).

        """
        max_timeout = runtime_variables.get("max_timeout")
        super().__init__(
            logger=logger or logging.getLogger(__name__),
            grace_period=grace_period,
            max_timeout=float(max_timeout) if max_timeout is not None else None,
        )
        self._resolved_flow = resolved_flow
        self._phase_registry = phase_registry
        self._runtime_variables = runtime_variables
        self._provider_registry = provider_registry
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._resume = resume
        self._checkpoint_manager = CheckpointManager(checkpoint_path)
        self._outcome_store = RunOutcomeStore(self._checkpoint_manager.outcome_path)
        self._agent_logger: AgentLogger | None = None
        self._failed_phase: str | None = None
        self._failed_error: str | None = None
        self._started_at: datetime | None = None
        self._resume_completed: set[str] = set()
        self._outcome: RunOutcome | None = None
        self._outcome_recording_error: RunOutcomeError | None = None
        self._resources: RunResources | None = None
        self._summary_task: asyncio.Task[RunSummaryAttempt] | None = None
        self._summary_cancellation_requested = False
        self._summarizer_factory = summarizer_factory

    @property
    def failed_phase(self) -> str | None:
        return self._failed_phase

    @property
    def outcome(self) -> RunOutcome | None:
        """Return the deterministic outcome after the run ends."""
        return self._outcome

    @property
    def outcome_recording_error(self) -> RunOutcomeError | None:
        """Return the error that prevented the outcome from being recorded for a failed run, if any."""
        return self._outcome_recording_error

    def run(self) -> None:
        """Run the flow and record its deterministic outcome."""
        asyncio.run(self._run_with_outcome())

    async def run_async(self) -> None:
        """Run the flow on the caller's event loop and record its deterministic outcome."""
        await self._run_with_outcome()

    def request_summary_cancellation(self) -> None:
        """Cancel only final-summary generation while preserving the deterministic result."""
        self._summary_cancellation_requested = True
        if self._summary_task is not None and not self._summary_task.done():
            self._summary_task.cancel()

    async def _run_with_outcome(self) -> None:
        self._started_at = datetime.now(UTC)
        try:
            await super().run_async()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            try:
                await self._record_outcome(e)
            except RunOutcomeError as outcome_error:
                self._logger.exception("Failed to record the outcome for a failed flow")
                self._outcome_recording_error = outcome_error
                e.add_note(f"Outcome recording also failed: {outcome_error}")
            raise
        else:
            await self._record_outcome(None)
        finally:
            if self._agent_logger is not None:
                self._agent_logger.close()

    async def _record_outcome(self, exception: BaseException | None) -> None:
        outcome, summary_started_at = await self._persist_generating_state(exception)
        try:
            await self._callbacks.fire_run_finalizing(outcome)
            attempt = await self._summarize_outcome(outcome, summary_started_at)
        except asyncio.CancelledError:
            self._persist_interrupted_summary(outcome, summary_started_at)
            raise
        await self._persist_final_state(outcome, attempt)

    async def _persist_generating_state(self, exception: BaseException | None) -> tuple[RunOutcome, datetime]:
        """Build the deterministic outcome, mark its summary as generating, and persist it."""
        try:
            finished_at = datetime.now(UTC)
            started_at = self._started_at or finished_at
            checkpoints = self._current_run_checkpoints(started_at)
            outcome = build_run_outcome(
                resolved_flow=self._resolved_flow,
                checkpoints=checkpoints,
                skipped_on_resume=self._resume_completed,
                started_at=started_at,
                finished_at=finished_at,
                run_dir=self._checkpoint_manager.run_dir,
                resumed=self._resume,
                exception=exception,
                failed_phase=self._failed_phase,
            )
        except Exception as e:
            raise RunOutcomeBuildError(f"Failed to build the flow outcome: {e}") from e

        summary_started_at = datetime.now(UTC)
        outcome = outcome.model_copy(
            update={
                "summary": RunSummaryMetadata(
                    status=RunSummaryStatus.GENERATING,
                    started_at=summary_started_at.isoformat(),
                )
            }
        )
        self._outcome = outcome
        try:
            self._outcome_store.write(outcome)
        except Exception as e:
            unavailable = _unavailable_summary(summary_started_at, f"Initial run outcome persistence failed: {e}")
            self._outcome = outcome.model_copy(update={"summary": unavailable})
            await self._callbacks.fire_run_finished(self._outcome)
            raise RunOutcomePersistenceError(f"Failed to persist the flow outcome: {e}") from e
        return outcome, summary_started_at

    def _persist_interrupted_summary(self, outcome: RunOutcome, summary_started_at: datetime) -> None:
        """Record that final-summary generation was interrupted, best-effort."""
        interrupted_outcome = outcome.model_copy(
            update={
                "summary": _unavailable_summary(
                    summary_started_at,
                    "Final summary generation was interrupted before completion",
                )
            }
        )
        self._outcome = interrupted_outcome
        try:
            self._outcome_store.write(interrupted_outcome)
        except Exception:
            self._logger.exception("Failed to persist the interrupted final-summary state")

    async def _persist_final_state(self, outcome: RunOutcome, attempt: RunSummaryAttempt) -> None:
        """Merge the summary attempt into the outcome, persist it, and notify listeners."""
        final_outcome = outcome.model_copy(update={"summary": attempt.metadata})
        self._outcome = final_outcome
        persistence_error: RunOutcomePersistenceError | None = None
        persistence_cause: Exception | None = None
        try:
            self._outcome_store.write(final_outcome)
        except Exception as e:
            persistence_cause = e
            persistence_error = RunOutcomePersistenceError(f"Failed to persist the final flow outcome: {e}")

        await self._callbacks.fire_run_finished(final_outcome)
        if persistence_error is not None:
            raise persistence_error from persistence_cause

    async def _summarize_outcome(self, outcome: RunOutcome, started_at: datetime) -> RunSummaryAttempt:
        if self._resources is None:
            return RunSummaryAttempt(
                metadata=_unavailable_summary(started_at, "Run resources were unavailable for summary generation")
            )
        try:
            summarizer = self._build_run_summarizer()
        except Exception as e:
            return RunSummaryAttempt(metadata=_unavailable_summary(started_at, f"Summary construction failed: {e}"))

        self._summary_task = asyncio.create_task(summarizer.summarize(outcome))
        if self._summary_cancellation_requested:
            self._summary_task.cancel()
        try:
            return await self._summary_task
        except asyncio.CancelledError:
            current_task = asyncio.current_task()
            if not self._summary_cancellation_requested or (current_task is not None and current_task.cancelling()):
                raise
            return RunSummaryAttempt(
                metadata=_unavailable_summary(started_at, "Final summary generation was stopped by the user")
            )
        finally:
            self._summary_task = None

    def _build_run_summarizer(self) -> RunSummarizerLike:
        if self._summarizer_factory is not None:
            return self._summarizer_factory()
        if self._resources is None:
            raise RuntimeError("Run resources are not initialized")
        return RunSummarizer(
            resolved_flow=self._resolved_flow,
            checkpoint_manager=self._checkpoint_manager,
            resources=self._resources,
            runtime_variables=self._runtime_variables,
        )

    def _current_run_checkpoints(self, started_at: datetime) -> dict[str, PhaseCheckpoint]:
        checkpoints = self._checkpoint_manager.read()
        return {
            phase_id: checkpoint
            for phase_id, checkpoint in checkpoints.items()
            if phase_id in self._resume_completed or _checkpoint_finished_at(checkpoint) >= started_at
        }

    async def on_initialize(self) -> None:
        """Construct phases from the resolved flow and submit the start PhaseTrigger."""
        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in self._resolved_flow.flow}

        completed, frontier = (
            resolve_resume_state(self._resolved_flow, self._checkpoint_manager) if self._resume else (set(), set())
        )
        self._resume_completed = completed
        if self._resume:
            self._logger.info(
                "Resuming: %d phase(s) completed, re-running frontier %r", len(completed), sorted(frontier)
            )

        self._agent_logger = AgentLogger(self._checkpoint_manager.agent_log_root)
        run_callbacks = self._callbacks.with_set(self._agent_logger.as_callback_set())

        self._resources = RunResources(
            provider_registry=self._provider_registry,
            file_access_policy=self._file_access_policy,
            agents=self._resolved_flow.agents,
            callbacks=run_callbacks,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=self._resolved_flow.variables,
            callbacks=run_callbacks,
            logger=self._logger,
            resume_frontier=frozenset(frontier),
        )

        for entry in self._resolved_flow.flow:
            if entry.phase in completed:
                self._logger.info("Resuming: skipping already-completed phase %r", entry.phase)
                continue
            phase_config = self._resolved_flow.phases[entry.phase]
            phase = self._phase_registry.get(phase_config.class_).build(
                phase_id=entry.phase,
                config=phase_config,
                deps=dependency_map[entry.phase],
                resources=self._resources,
                checkpoint_manager=self._checkpoint_manager,
                context=context,
            )
            self.register_processor(phase, [PhaseTrigger])

        self.submit_message(PhaseTrigger(id="start", phase_id=None))
        for entry in self._resolved_flow.flow:
            if entry.phase in completed:
                self.submit_message(PhaseTrigger(id=f"{entry.phase}_resumed", phase_id=entry.phase))

    async def on_message_received(self, message: BaseMessage) -> None:
        """Stop the entire pipeline immediately when any phase fails."""
        if isinstance(message, PhaseFailedMessage):
            self._failed_phase = message.phase_id
            self._failed_error = message.error
            error = FatalProcessingError(f"Phase '{message.phase_id}' failed: {message.error}")
            await self._callbacks.fire_run_error()
            raise error

    async def on_error(self, error: OrchestratorHookError) -> None:
        """Stop the run after an unexpected orchestrator failure."""
        raise FatalProcessingError(str(error)) from error.original_exception

    async def on_finalize(self, exception: Exception | None) -> None:
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )


def _checkpoint_finished_at(checkpoint: PhaseCheckpoint) -> datetime:
    """Return an aware timestamp suitable for filtering checkpoints from older attempts."""
    try:
        finished_at = datetime.fromisoformat(checkpoint.finished_at)
    except ValueError as e:
        raise ValueError(f"Checkpoint has invalid finished_at timestamp {checkpoint.finished_at!r}") from e

    if finished_at.tzinfo is None:
        return finished_at.replace(tzinfo=UTC)

    return finished_at


def _unavailable_summary(started_at: datetime, error: str) -> RunSummaryMetadata:
    return RunSummaryMetadata.finished(status=RunSummaryStatus.UNAVAILABLE, started_at=started_at, error=error)
