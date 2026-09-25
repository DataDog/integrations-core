# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Run-directory helpers: locate a flow's run directory and read its resume state."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ddev.ai.config.models import ResolvedFlow
from ddev.ai.runtime.checkpoints import CheckpointManager, CheckpointReadError, ResumeState


def flow_slug(flow: ResolvedFlow) -> str:
    """Return a readable, collision-resistant filesystem slug for a flow."""
    name = flow.name or "unnamed"
    readable = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def ai_runs_dir(repo_root: str | Path) -> Path:
    """Return the shared run root below a repository."""
    return Path(repo_root) / ".ddev" / "ai-runs"


def flow_resume_state(flow: ResolvedFlow, runs_dir: Path) -> ResumeState:
    """Return the resume state recorded for *flow* below *runs_dir*.

    Unreadable checkpoints are reported through ``ResumeState.error`` rather than raised, so one
    corrupt file cannot crash a grid of flows. The reason is kept so callers can tell a corrupt
    file apart from a clean slate and surface the remedy.

    Args:
        flow: The flow whose run directory to inspect.
        runs_dir: Base directory that contains per-flow run sub-directories.
    """
    manager = CheckpointManager(runs_dir / flow_slug(flow) / "checkpoints.yaml")
    try:
        return manager.resume_state(flow)
    except CheckpointReadError as e:
        return ResumeState(error=str(e))
