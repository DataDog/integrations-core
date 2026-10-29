# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ddev.ai.config.errors import ConfigError
from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.tools.shell.base import run_command
from ddev.utils.integration_naming import integration_dir_name

if TYPE_CHECKING:
    from ddev.ai.config.models import PhaseConfig
    from ddev.ai.phases.base import FlowContext
    from ddev.ai.phases.resources import PhaseResources
    from ddev.ai.runtime.checkpoints import CheckpointManager
    from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


class ApiScaffoldPhase(Phase):
    """Create a check scaffold or hand off an existing directory without modifying it."""

    def __init__(
        self,
        phase_id: str,
        dependencies: list[str],
        config: PhaseConfig,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
        file_access_policy: FileAccessPolicy,
    ) -> None:
        super().__init__(phase_id, dependencies, config, checkpoint_manager, context)
        self._file_access_policy = file_access_policy

    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        if config.agent is not None or config.tasks or config.checkpoint is not None:
            raise ConfigError(f"Phase {phase_id!r} (ApiScaffoldPhase) does not accept agent, tasks, or checkpoint")

    @classmethod
    def build(
        cls,
        phase_id: str,
        config: PhaseConfig,
        deps: list[str],
        resources: PhaseResources,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> ApiScaffoldPhase:
        return cls(phase_id, deps, config, checkpoint_manager, context, resources.file_access_policy)

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        display_name = context.get("integration")
        if not isinstance(display_name, str):
            raise ConfigError(f"Phase {self._phase_id!r}: 'integration' must be a display name")
        try:
            directory = integration_dir_name(display_name)
        except ValueError as error:
            raise ConfigError(f"Phase {self._phase_id!r}: {error}") from error

        root = self._file_access_policy.write_root
        target = root / directory
        if target.is_symlink():
            raise ConfigError(f"Refusing to scaffold a symlink target: {target}")
        self._file_access_policy.assert_writable(target)
        if target.exists() and not target.is_dir():
            raise ConfigError(f"Integration target exists but is not a directory: {target}")

        existed = target.is_dir()
        command: list[str] = []
        if not existed:
            command = ["ddev", "--no-interactive", "create", "check", display_name, "--location", str(root)]
            result = await run_command(command, timeout=60)
            if not result.success:
                raise RuntimeError(f"Scaffolding {target} failed: {result.error or result.data}")
            if not target.is_dir() or target.is_symlink():
                raise RuntimeError(f"Scaffold command succeeded but did not create the expected directory: {target}")

        expected_files = [
            "manifest.json",
            "pyproject.toml",
            f"datadog_checks/{directory}/__init__.py",
            f"datadog_checks/{directory}/check.py",
            "assets/configuration/spec.yaml",
            "metadata.csv",
            "README.md",
            "tests/conftest.py",
        ]
        present = [path for path in expected_files if (target / path).is_file()]
        missing = [path for path in expected_files if path not in present]
        if missing and not existed:
            raise RuntimeError(f"Scaffold is incomplete at {target}; missing: {', '.join(missing)}")

        warnings: list[str] = []
        if existed:
            warnings.append(
                "Directory already existed; scaffolding was skipped and no files were changed. "
                "It may contain an implementation or a partial scaffold. Inspect current files and preserve "
                "existing work; do not assume boilerplate or successful prior generation."
            )
        if missing:
            warnings.append(f"Expected scaffold files missing: {', '.join(missing)}. Reconcile these during build.")

        status = "existing" if existed else "created"
        lines = [
            f"Scaffold status: {status}",
            f"Display name: {display_name}",
            f"Integration directory: {directory}",
            f"Target path: {target}",
        ]
        lines.append("Observed scaffold files (relative to target): " + (", ".join(present) or "none"))
        lines.extend(f"Warning: {warning}" for warning in warnings)
        lines.append("File presence does not establish implementation completeness or passing validation.")
        return PhaseOutcome(
            memory_text="\n".join(lines),
            checkpoint_data={
                "status": status,
                "display_name": display_name,
                "directory": directory,
                "target_path": str(target),
                "command": command,
                "present_files": present,
                "missing_files": missing,
                "warnings": warnings,
            },
        )
