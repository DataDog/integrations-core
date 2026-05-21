# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anthropic

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree, prepare_agent_worktree
from ddev.ai.phases.orchestrator import PhaseOrchestrator
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

FLOW_DIR = Path(__file__).parent


class E2EFrameworkLabFlowError(Exception):
    """Raised when the E2E framework lab AI flow cannot complete."""


@dataclass(frozen=True)
class E2EFrameworkLabFlowResult:
    """Result of preparing and running the E2E framework lab AI flow."""

    worktree: AgentWorktree
    checkpoint_path: Path


def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    agent_repo_path: Path,
    agent_worktree_parent: Path,
    anthropic_client: anthropic.AsyncAnthropic,
    branch_name: str | None = None,
    callbacks: Callbacks | None = None,
) -> E2EFrameworkLabFlowResult:
    """Create an Agent worktree and run the E2E framework lab generation flow."""

    resolved_integration_path = integration_path.expanduser().resolve(strict=False)
    if not resolved_integration_path.is_dir():
        raise E2EFrameworkLabFlowError(f"Integration path does not exist: {resolved_integration_path}")

    worktree = prepare_agent_worktree(
        integration=integration,
        agent_repo_path=agent_repo_path,
        worktree_parent=agent_worktree_parent,
        branch_name=branch_name,
    )
    checkpoint_path = worktree.path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    runtime_variables = {
        "integration": integration,
        "integration_path": str(resolved_integration_path),
        "agent_repo_path": str(worktree.repo_path),
        "agent_worktree_path": str(worktree.path),
        "branch_name": worktree.branch_name,
    }

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=FLOW_DIR / "flow.yaml",
        checkpoint_path=checkpoint_path,
        runtime_variables=runtime_variables,
        anthropic_client=anthropic_client,
        file_access_policy=FileAccessPolicy(write_root=worktree.path),
        callbacks=callbacks,
    )

    try:
        orchestrator.run()
    except Exception as e:
        raise E2EFrameworkLabFlowError(
            "E2E framework lab flow failed. "
            f"Agent worktree: {worktree.path}. "
            f"Checkpoint path: {checkpoint_path}. "
            f"Original error: {e}"
        ) from e

    return E2EFrameworkLabFlowResult(worktree=worktree, checkpoint_path=checkpoint_path)
