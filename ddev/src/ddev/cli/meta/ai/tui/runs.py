# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Run-directory helpers: detect whether a resumable run exists for a flow."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.runtime.checkpoints import CheckpointManager, resolve_resume_state


def flow_slug(flow: ResolvedFlow) -> str:
    """Return a readable, collision-resistant filesystem slug for a flow."""
    name = flow.name or "unnamed"
    readable = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def ai_runs_dir(repo_root: str | Path) -> Path:
    """Return the shared run root below a repository."""
    return Path(repo_root) / ".ddev" / "ai-runs"


def has_resumable_run(flow: ResolvedFlow, runs_dir: Path) -> bool:
    """Return True if an incomplete run exists for *flow*.

    A run is resumable when ``checkpoints.yaml`` exists inside the flow's run
    directory, is non-empty, and ``resolve_resume_state`` (the same logic the
    orchestrator uses to resume) finds at least one scheduled phase that
    hasn't reached a dependency-closed success.

    Args:
        flow: The flow to check.
        runs_dir: Base directory that contains per-flow run sub-directories.
    """
    checkpoints_path = runs_dir / flow_slug(flow) / "checkpoints.yaml"
    if not checkpoints_path.exists():
        return False

    manager = CheckpointManager(checkpoints_path)
    try:
        checkpoints = manager.read()
    except Exception:
        return False

    if not checkpoints:
        return False

    try:
        completed, _frontier = resolve_resume_state(flow, manager)
    except ConfigError:
        return False

    scheduled = {entry.phase for entry in flow.flow}
    return completed != scheduled


def resume_completed_phases(flow: ResolvedFlow, runs_dir: Path) -> set[str]:
    """Return dependency-closed completed phases from the flow checkpoint."""
    manager = CheckpointManager(runs_dir / flow_slug(flow) / "checkpoints.yaml")
    completed, _frontier = resolve_resume_state(flow, manager)
    return completed
