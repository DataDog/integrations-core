from unittest.mock import MagicMock

import pytest
import yaml

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowError, prepare_and_run_e2e_lab_flow


class CapturingOrchestrator:
    instances = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.ran = False
        CapturingOrchestrator.instances.append(self)

    def run(self) -> None:
        self.ran = True
        self.kwargs["checkpoint_path"].write_text(
            yaml.safe_dump(
                {
                    "research_technology": {"status": "success"},
                    "design_lab_topology": {"status": "success"},
                    "design_metric_workload": {"status": "success"},
                    "review_lab_design": {"status": "success"},
                    "generate_component": {"status": "success"},
                    "generate_scenario": {"status": "success"},
                    "generate_lab_manifest": {"status": "success"},
                    "review_lab": {"status": "success"},
                }
            )
        )


class IncompleteOrchestrator(CapturingOrchestrator):
    def run(self) -> None:
        self.ran = True
        self.kwargs["checkpoint_path"].write_text(yaml.safe_dump({"research_technology": {"status": "success"}}))


class FailingOrchestrator(CapturingOrchestrator):
    def run(self) -> None:
        raise RuntimeError("phase failed")


def test_prepare_and_run_e2e_lab_flow_wires_orchestrator_to_integration_lab_path(tmp_path, monkeypatch) -> None:
    CapturingOrchestrator.instances = []
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", CapturingOrchestrator)

    mock_client = MagicMock()
    result = prepare_and_run_e2e_lab_flow(
        integration="redisdb",
        integration_path=integration_path,
        anthropic_client=mock_client,
    )

    expected_lab_path = integration_path / "e2e_lab"
    assert result.lab_path == expected_lab_path
    assert result.checkpoint_path == expected_lab_path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    assert expected_lab_path.is_dir()

    orchestrator = CapturingOrchestrator.instances[0]
    assert orchestrator.ran is True
    assert orchestrator.kwargs["runtime_variables"] == {
        "integration": "redisdb",
        "integration_path": str(integration_path.resolve(strict=False)),
        "lab_path": str(expected_lab_path.resolve(strict=False)),
    }
    assert orchestrator.kwargs["agent_clients"] == {"anthropic": mock_client}
    assert orchestrator.kwargs["file_access_policy"].write_root == expected_lab_path.resolve(strict=False)
    assert orchestrator.kwargs["max_timeout"] == 3600


def test_prepare_and_run_e2e_lab_flow_rejects_missing_integration_path(tmp_path) -> None:
    with pytest.raises(E2EFrameworkLabFlowError, match="Integration path does not exist"):
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=tmp_path / "missing",
            anthropic_client=MagicMock(),
        )


def test_prepare_and_run_e2e_lab_flow_reports_incomplete_flow_with_paths(tmp_path, monkeypatch) -> None:
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", IncompleteOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "Flow did not complete successfully" in message
    assert "design_lab_topology" in message
    assert str(integration_path / "e2e_lab") in message
    assert "checkpoints.yaml" in message


def test_prepare_and_run_e2e_lab_flow_reports_phase_failure_with_paths(tmp_path, monkeypatch) -> None:
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", FailingOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "phase failed" in message
    assert str(integration_path / "e2e_lab") in message
    assert "checkpoints.yaml" in message
