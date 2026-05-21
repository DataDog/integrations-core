import subprocess

import pytest

from ddev.ai.flows.e2e_framework_lab.worktree import (
    AgentWorktree,
    E2ELabWorktreeError,
    _sanitize_branch_fragment,
    prepare_agent_worktree,
)


class GitRecorder:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.show_ref_returncode = 1

    def run(self, command, *, stdout, stderr, text, check):
        rendered = [str(part) for part in command]
        self.commands.append(rendered)
        if "show-ref" in rendered:
            return subprocess.CompletedProcess(rendered, self.show_ref_returncode, "", "")
        if "rev-parse" in rendered:
            return subprocess.CompletedProcess(rendered, 0, "/tmp/datadog-agent\n", "")
        if "remote" in rendered:
            return subprocess.CompletedProcess(rendered, 0, "git@github.com:DataDog/datadog-agent.git\n", "")
        return subprocess.CompletedProcess(rendered, 0, "", "")


def test_sanitize_branch_fragment() -> None:
    assert _sanitize_branch_fragment("OpenMetrics V2") == "openmetrics-v2"
    assert _sanitize_branch_fragment("postgres_db") == "postgres-db"
    assert _sanitize_branch_fragment("___") == "integration"


def test_prepare_agent_worktree_creates_branch_from_origin_main(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree_parent = tmp_path / "worktrees"

    result = prepare_agent_worktree(
        integration="OpenMetrics V2",
        agent_repo_path=agent_repo,
        worktree_parent=worktree_parent,
        branch_name=None,
    )

    assert result == AgentWorktree(
        repo_path=agent_repo,
        path=worktree_parent / "e2e-lab-openmetrics-v2",
        branch_name="e2e-lab-openmetrics-v2",
    )
    assert recorder.commands[-2] == ["git", "-C", str(agent_repo), "fetch", "origin", "main"]
    assert recorder.commands[-1] == [
        "git",
        "-C",
        str(agent_repo),
        "worktree",
        "add",
        "-b",
        "e2e-lab-openmetrics-v2",
        str(worktree_parent / "e2e-lab-openmetrics-v2"),
        "origin/main",
    ]


def test_prepare_agent_worktree_rejects_missing_repo(tmp_path) -> None:
    with pytest.raises(E2ELabWorktreeError, match="Agent repo path does not exist"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=tmp_path / "missing",
            worktree_parent=tmp_path / "worktrees",
        )


def test_prepare_agent_worktree_rejects_existing_worktree_path(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    existing = tmp_path / "worktrees" / "custom-branch"
    existing.mkdir(parents=True)

    with pytest.raises(E2ELabWorktreeError, match="Worktree path already exists"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=agent_repo,
            worktree_parent=tmp_path / "worktrees",
            branch_name="custom-branch",
        )


def test_prepare_agent_worktree_rejects_existing_branch(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    recorder.show_ref_returncode = 0
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()

    with pytest.raises(E2ELabWorktreeError, match="Branch already exists"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=agent_repo,
            worktree_parent=tmp_path / "worktrees",
            branch_name="custom-branch",
        )
