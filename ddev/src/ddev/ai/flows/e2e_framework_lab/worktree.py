# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class E2ELabWorktreeError(Exception):
    """Raised when the Agent worktree cannot be prepared."""


@dataclass(frozen=True)
class AgentWorktree:
    """Describes the freshly-created Agent worktree used by the AI flow."""

    repo_path: Path
    path: Path
    branch_name: str


def _sanitize_branch_fragment(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "integration"


def default_branch_name(integration: str) -> str:
    """Return the default Agent branch name for a generated lab."""

    return f"e2e-lab-{_sanitize_branch_fragment(integration)}"


def prepare_agent_worktree(
    *,
    integration: str,
    agent_repo_path: Path,
    worktree_parent: Path,
    branch_name: str | None = None,
) -> AgentWorktree:
    """Fetch latest Agent main and create a dedicated worktree for generated lab files."""

    repo_path = agent_repo_path.expanduser().resolve(strict=False)
    if not repo_path.is_dir():
        raise E2ELabWorktreeError(f"Agent repo path does not exist: {repo_path}")

    _validate_agent_repo(repo_path)

    resolved_branch_name = branch_name or default_branch_name(integration)
    worktree_path = (worktree_parent.expanduser().resolve(strict=False) / resolved_branch_name).resolve(strict=False)

    if worktree_path.exists():
        raise E2ELabWorktreeError(f"Worktree path already exists: {worktree_path}")
    if _branch_exists(repo_path, resolved_branch_name):
        raise E2ELabWorktreeError(f"Branch already exists in Agent repo: {resolved_branch_name}")

    worktree_parent.mkdir(parents=True, exist_ok=True)
    _run_git(repo_path, "fetch", "origin", "main")
    _run_git(repo_path, "worktree", "add", "-b", resolved_branch_name, str(worktree_path), "origin/main")

    return AgentWorktree(repo_path=repo_path, path=worktree_path, branch_name=resolved_branch_name)


def _validate_agent_repo(repo_path: Path) -> None:
    _run_git(repo_path, "rev-parse", "--show-toplevel")
    origin = _run_git(repo_path, "remote", "get-url", "origin")
    if "datadog-agent" not in origin.lower():
        raise E2ELabWorktreeError(f"Git origin does not look like datadog-agent: {origin.strip()}")


def _branch_exists(repo_path: Path, branch_name: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _run_git(repo_path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        output = e.stdout or ""
        raise E2ELabWorktreeError(f"git {' '.join(args)} failed in {repo_path}:\n{output}") from e
    return result.stdout
