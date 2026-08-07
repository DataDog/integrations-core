# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import AgentConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.goal import DeterministicCheck
from ddev.ai.phases.openmetrics.inspect_endpoint import normalize_endpoint_name
from ddev.ai.phases.openmetrics.label_hygiene import LabelHygieneError, lint_label_hygiene
from ddev.ai.runtime.checkpoints import CheckpointManager, SuccessCheckpoint

if TYPE_CHECKING:
    from ddev.ai.phases.resources import PhaseResources
    from ddev.ai.react.factory import ReActProcessFactory

INSPECTION_PHASE_ID = "inspect_endpoint"
CODE_TASK_NAME = "write_code"


class OpenMetricsBuildPhase(AgenticPhase):
    """Build an OpenMetrics integration with deterministic checks before task acceptance."""

    def __init__(
        self,
        phase_id: str,
        dependencies: list[str],
        config: PhaseConfig,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
        agent_config: AgentConfig,
        process_factory: ReActProcessFactory,
        write_root: Path,
    ) -> None:
        super().__init__(
            phase_id=phase_id,
            dependencies=dependencies,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
            agent_config=agent_config,
            process_factory=process_factory,
        )
        self._write_root = write_root

    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        super().validate_config(phase_id, config)
        code_tasks = [task for task in config.tasks if task.name == CODE_TASK_NAME]
        if len(code_tasks) != 1:
            raise ConfigError(
                f"Phase {phase_id!r} (OpenMetricsBuildPhase) requires exactly one task named {CODE_TASK_NAME!r}"
            )

    @classmethod
    def build(
        cls,
        phase_id: str,
        config: PhaseConfig,
        deps: list[str],
        resources: PhaseResources,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> OpenMetricsBuildPhase:
        agent_name = cast(str, config.agent)
        return cls(
            phase_id=phase_id,
            dependencies=deps,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
            agent_config=resources.agent_config(agent_name),
            process_factory=resources.process_factory,
            write_root=resources.write_root,
        )

    def deterministic_checks(self, task: TaskConfig, context: dict[str, Any]) -> tuple[DeterministicCheck, ...]:
        checks = super().deterministic_checks(task, context)
        if task.name != CODE_TASK_NAME:
            return checks
        return (*checks, DeterministicCheck(name="label hygiene", run=lambda: self._check_label_hygiene(context)))

    def _check_label_hygiene(self, context: dict[str, Any]) -> str | None:
        """Validate captured label catalogs against the generated check configuration."""
        integration = context.get("integration")
        if not isinstance(integration, str):
            raise ConfigError("'integration' runtime variable must be a string")
        try:
            integration_name = normalize_endpoint_name(integration)
        except ValueError as e:
            raise ConfigError(f"invalid 'integration' runtime variable: {e}") from e

        catalog_paths = self._catalog_paths(context)
        check_path = (self._write_root / integration_name / "datadog_checks" / integration_name / "check.py").resolve()
        if not check_path.is_file() and (misplaced_check := self._find_misplaced_check(integration_name)) is not None:
            raise LabelHygieneError(
                f"Expected generated check at {check_path}, but found it at {misplaced_check}; "
                "the scaffolded integration name does not match the normalized runtime name"
            )
        result = lint_label_hygiene(catalog_paths, check_path)
        return result.failure_reason(check_path)

    def _find_misplaced_check(self, integration_name: str) -> Path | None:
        """Find a generated check whose package normalizes to the expected name."""
        for path in self._write_root.glob("*/datadog_checks/*/check.py"):
            try:
                if normalize_endpoint_name(path.parent.name) == integration_name:
                    return path.resolve()
            except ValueError:
                continue
        return None

    @staticmethod
    def _catalog_paths(context: dict[str, Any]) -> list[Path]:
        """Read authoritative catalog paths from the successful inspection checkpoint."""
        checkpoints = context.get("checkpoints")
        if not isinstance(checkpoints, dict):
            raise LabelHygieneError("Phase context does not contain checkpoints")
        checkpoint = checkpoints.get(INSPECTION_PHASE_ID)
        if not isinstance(checkpoint, SuccessCheckpoint):
            raise LabelHygieneError(f"Successful {INSPECTION_PHASE_ID!r} checkpoint is required")
        endpoints = checkpoint.phase_data.get("endpoints")
        if not isinstance(endpoints, list) or not endpoints:
            raise LabelHygieneError("Inspection checkpoint contains no endpoint catalogs")

        paths: list[Path] = []
        for endpoint in endpoints:
            if not isinstance(endpoint, dict) or not isinstance(endpoint.get("metrics_jsonl_path"), str):
                raise LabelHygieneError("Inspection checkpoint contains an invalid endpoint catalog entry")
            paths.append(Path(endpoint["metrics_jsonl_path"]))
        return paths
