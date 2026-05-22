# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anthropic
import yaml

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import FlowConfig
from ddev.ai.phases.orchestrator import PhaseOrchestrator
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

FLOW_DIR = Path(__file__).parent
DEFAULT_MAX_TIMEOUT = 3600
LAB_DIRECTORY_NAME = "e2e_lab"


class E2EFrameworkLabFlowError(Exception):
    """Raised when the E2E framework lab AI flow cannot complete."""


@dataclass(frozen=True)
class E2EFrameworkLabFlowResult:
    """Result of running the E2E framework lab AI flow."""

    lab_path: Path
    checkpoint_path: Path


def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    anthropic_client: anthropic.AsyncAnthropic,
    callbacks: Callbacks | None = None,
    max_timeout: float = DEFAULT_MAX_TIMEOUT,
) -> E2EFrameworkLabFlowResult:
    """Create the integration lab directory and run the E2E framework lab generation flow."""

    resolved_integration_path = integration_path.expanduser().resolve(strict=False)
    if not resolved_integration_path.is_dir():
        raise E2EFrameworkLabFlowError(f"Integration path does not exist: {resolved_integration_path}")

    lab_path = resolved_integration_path / LAB_DIRECTORY_NAME
    lab_path.mkdir(parents=True, exist_ok=True)
    checkpoint_path = lab_path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    runtime_variables = {
        "integration": integration,
        "integration_path": str(resolved_integration_path),
        "lab_path": str(lab_path),
    }

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=FLOW_DIR / "flow.yaml",
        checkpoint_path=checkpoint_path,
        runtime_variables=runtime_variables,
        agent_clients={"anthropic": anthropic_client},
        file_access_policy=FileAccessPolicy(write_root=lab_path),
        callbacks=callbacks,
        max_timeout=max_timeout,
    )

    try:
        orchestrator.run()
    except Exception as e:
        raise E2EFrameworkLabFlowError(
            "E2E framework lab flow failed. "
            f"Integration lab path: {lab_path}. "
            f"Checkpoint path: {checkpoint_path}. "
            f"Original error: {e}"
        ) from e

    try:
        _assert_flow_completed(checkpoint_path)
    except E2EFrameworkLabFlowError as e:
        raise E2EFrameworkLabFlowError(f"{e} Integration lab path: {lab_path}.") from e

    return E2EFrameworkLabFlowResult(lab_path=lab_path, checkpoint_path=checkpoint_path)


def _assert_flow_completed(checkpoint_path: Path) -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)
    expected_phases = [entry.phase for entry in config.flow]
    try:
        checkpoints = yaml.safe_load(checkpoint_path.read_text()) or {}
    except OSError as e:
        raise E2EFrameworkLabFlowError(f"Flow did not write checkpoints: {checkpoint_path}") from e

    incomplete_phases = [
        phase_id for phase_id in expected_phases if checkpoints.get(phase_id, {}).get("status") != "success"
    ]
    if incomplete_phases:
        raise E2EFrameworkLabFlowError(
            "Flow did not complete successfully. "
            f"Incomplete phases: {', '.join(incomplete_phases)}. "
            f"Checkpoint path: {checkpoint_path}."
        )
