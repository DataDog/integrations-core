from unittest.mock import MagicMock

import pytest

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowError, prepare_and_run_e2e_lab_flow
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree


class CapturingOrchestrator:
    instances = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.ran = False
        CapturingOrchestrator.instances.append(self)

    def run(self) -> None:
        self.ran = True


class FailingOrchestrator(CapturingOrchestrator):
    def run(self) -> None:
        raise RuntimeError("phase failed")


def test_prepare_and_run_e2e_lab_flow_wires_orchestrator(tmp_path, monkeypatch) -> None:
    CapturingOrchestrator.instances = []
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree = AgentWorktree(
        repo_path=agent_repo,
        path=tmp_path / "agent-worktree",
        branch_name="e2e-lab-redisdb",
    )
    worktree.path.mkdir()

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.prepare_agent_worktree", lambda **kwargs: worktree)
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", CapturingOrchestrator)

    result = prepare_and_run_e2e_lab_flow(
        integration="redisdb",
        integration_path=integration_path,
        agent_repo_path=agent_repo,
        agent_worktree_parent=tmp_path / "worktrees",
        anthropic_client=MagicMock(),
    )

    assert result.worktree == worktree
    assert result.checkpoint_path == worktree.path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    orchestrator = CapturingOrchestrator.instances[0]
    assert orchestrator.ran is True
    assert orchestrator.kwargs["runtime_variables"] == {
        "integration": "redisdb",
        "integration_path": str(integration_path),
        "agent_repo_path": str(agent_repo),
        "agent_worktree_path": str(worktree.path),
        "branch_name": "e2e-lab-redisdb",
    }
    assert orchestrator.kwargs["file_access_policy"].write_root == worktree.path.resolve(strict=False)


def test_prepare_and_run_e2e_lab_flow_rejects_missing_integration_path(tmp_path) -> None:
    with pytest.raises(E2EFrameworkLabFlowError, match="Integration path does not exist"):
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=tmp_path / "missing",
            agent_repo_path=tmp_path / "datadog-agent",
            agent_worktree_parent=tmp_path / "worktrees",
            anthropic_client=MagicMock(),
        )


def test_prepare_and_run_e2e_lab_flow_reports_phase_failure_with_paths(tmp_path, monkeypatch) -> None:
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree = AgentWorktree(
        repo_path=agent_repo,
        path=tmp_path / "agent-worktree",
        branch_name="e2e-lab-redisdb",
    )
    worktree.path.mkdir()

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.prepare_agent_worktree", lambda **kwargs: worktree)
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", FailingOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            agent_repo_path=agent_repo,
            agent_worktree_parent=tmp_path / "worktrees",
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "phase failed" in message
    assert str(worktree.path) in message
    assert "checkpoints.yaml" in message
