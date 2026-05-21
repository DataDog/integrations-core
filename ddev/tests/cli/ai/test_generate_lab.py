from unittest.mock import MagicMock

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowResult
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree
from tests.helpers.runner import CliRunner


def test_ai_group_is_registered(ddev: CliRunner) -> None:
    result = ddev("ai", "--help")

    assert result.exit_code == 0
    assert "generate-lab" in result.output


def test_generate_lab_requires_anthropic_api_key(ddev: CliRunner, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY must be set" in result.output


def test_generate_lab_uses_configured_agent_repo_by_default(
    ddev: CliRunner, config_file, mocker, monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    agent_repo = tmp_path / "datadog-agent"
    config_file.model.repos["agent"] = str(agent_repo)
    config_file.save()
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    result_value = E2EFrameworkLabFlowResult(
        worktree=AgentWorktree(
            repo_path=agent_repo,
            path=tmp_path / "datadog-agent-worktrees" / "e2e-lab-redisdb",
            branch_name="e2e-lab-redisdb",
        ),
        checkpoint_path=tmp_path / "datadog-agent-worktrees" / "e2e-lab-redisdb" / ".ddev-ai" / "checkpoints.yaml",
    )
    get_integration = mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    runner = mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", return_value=result_value)
    client_cls = mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 0
    get_integration.assert_called_once_with("redisdb")
    runner.assert_called_once()
    kwargs = runner.call_args.kwargs
    assert kwargs["integration"] == "redisdb"
    assert kwargs["integration_path"] == integration.path
    assert kwargs["agent_repo_path"] == agent_repo
    assert kwargs["agent_worktree_parent"] == tmp_path / "datadog-agent-worktrees"
    assert kwargs["branch_name"] is None
    assert kwargs["anthropic_client"] == client_cls.return_value
    assert "Agent worktree" in result.output
    assert "dda inv aws.create-redisdb" in result.output


def test_generate_lab_forwards_path_and_branch_overrides(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    agent_repo = tmp_path / "agent"
    worktree_parent = tmp_path / "agent-wt"
    integration = MagicMock(path=tmp_path / "integrations-core" / "nginx")
    result_value = E2EFrameworkLabFlowResult(
        worktree=AgentWorktree(
            repo_path=agent_repo,
            path=worktree_parent / "custom-branch",
            branch_name="custom-branch",
        ),
        checkpoint_path=worktree_parent / "custom-branch" / ".ddev-ai" / "checkpoints.yaml",
    )
    mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    runner = mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", return_value=result_value)
    mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")

    result = ddev(
        "ai",
        "generate-lab",
        "nginx",
        "--agent-repo",
        str(agent_repo),
        "--worktree-parent",
        str(worktree_parent),
        "--branch-name",
        "custom-branch",
    )

    assert result.exit_code == 0
    kwargs = runner.call_args.kwargs
    assert kwargs["agent_repo_path"] == agent_repo
    assert kwargs["agent_worktree_parent"] == worktree_parent
    assert kwargs["branch_name"] == "custom-branch"
    assert "custom-branch" in result.output


def test_generate_lab_reports_runner_failure(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")
    mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", side_effect=RuntimeError("flow failed"))

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 1
    assert "flow failed" in result.output
