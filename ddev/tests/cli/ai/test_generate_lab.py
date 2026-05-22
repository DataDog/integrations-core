from unittest.mock import MagicMock

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowResult
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


def test_generate_lab_writes_to_integration_lab_path(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    result_value = E2EFrameworkLabFlowResult(
        lab_path=integration.path / "e2e_lab",
        checkpoint_path=integration.path / "e2e_lab" / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml",
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
    assert kwargs["anthropic_client"] == client_cls.return_value
    assert set(kwargs) == {"integration", "integration_path", "anthropic_client"}
    assert "Lab path" in result.output
    assert "redisdb/e2e_lab" in result.output


def test_generate_lab_reports_runner_failure(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")
    mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", side_effect=RuntimeError("flow failed"))

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 1
    assert "flow failed" in result.output
