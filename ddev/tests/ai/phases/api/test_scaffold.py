# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import CheckpointConfig, PhaseConfig, RuntimeVariables, TaskConfig
from ddev.ai.phases.api import scaffold as scaffold_module
from ddev.ai.phases.api.scaffold import ApiScaffoldPhase
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseTrigger
from ddev.ai.runtime.checkpoints import CheckpointManager, SuccessCheckpoint
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

PHASE_ID = "api_scaffold"
DISPLAY_NAME = "Example API-Service"
DIRECTORY = "example_api_service"
SCAFFOLD_FILES = (
    "manifest.json",
    "pyproject.toml",
    f"datadog_checks/{DIRECTORY}/__init__.py",
    f"datadog_checks/{DIRECTORY}/check.py",
    "assets/configuration/spec.yaml",
    "metadata.csv",
    "README.md",
    "tests/conftest.py",
)


def _make_phase(repo_root: Path) -> tuple[ApiScaffoldPhase, CheckpointManager]:
    checkpoint_manager = CheckpointManager(repo_root / ".ddev/ai-runs/api/checkpoints.yaml")
    resources = RunResources(
        provider_registry=AgentProviderRegistry(),
        file_access_policy=FileAccessPolicy(repo_root, DISPLAY_NAME),
        agents={},
        callbacks=Callbacks(),
    )
    phase = ApiScaffoldPhase.build(
        phase_id=PHASE_ID,
        config=PhaseConfig(name=PHASE_ID, class_="ApiScaffoldPhase"),
        deps=[],
        resources=resources,
        checkpoint_manager=checkpoint_manager,
        context=FlowContext(runtime_variables={"integration": DISPLAY_NAME}, flow_variables={}),
    )
    return phase, checkpoint_manager


def _write_scaffold(target: Path) -> None:
    for relative_path in SCAFFOLD_FILES:
        path = target / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Content for {relative_path}", encoding="utf-8")


async def test_create_uses_repository_policy_and_persists_handoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Creation must use the selected repository even when the process runs elsewhere."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    other_directory = tmp_path / "elsewhere"
    other_directory.mkdir()
    monkeypatch.chdir(other_directory)
    target = repo_root / DIRECTORY

    async def create(cmd: list[str], timeout: int) -> ToolResult:
        # Model the CLI's location handling so the test detects an incorrect destination.
        location = Path(cmd[cmd.index("--location") + 1])
        _write_scaffold(location / DIRECTORY)
        return ToolResult(success=True)

    command = AsyncMock(side_effect=create)
    monkeypatch.setattr(scaffold_module, "run_command", command)
    phase, checkpoint_manager = _make_phase(repo_root)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    command.assert_awaited_once_with(
        ["ddev", "--no-interactive", "create", "check", DISPLAY_NAME, "--location", str(repo_root)],
        timeout=60,
    )
    checkpoint = checkpoint_manager.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    assert checkpoint.phase_data["status"] == "created"
    assert checkpoint.phase_data["directory"] == DIRECTORY
    assert checkpoint.phase_data["target_path"] == str(target)
    assert "manifest.json" in checkpoint.phase_data["present_files"]
    assert checkpoint.phase_data["missing_files"] == []
    assert checkpoint.phase_data["warnings"] == []
    memory = checkpoint_manager.resolve_template_variable(f"{PHASE_ID}_memory")
    assert "Scaffold status: created" in memory
    assert DISPLAY_NAME in memory
    assert str(target) in memory
    assert "manifest.json" in memory
    assert not (other_directory / DIRECTORY).exists()


@pytest.mark.parametrize("missing_file", [None, "manifest.json"], ids=["complete", "partial"])
async def test_existing_directory_is_preserved_and_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing_file: str | None
):
    """Reusing complete or partial directories must preserve work and report observed gaps."""
    target = tmp_path / DIRECTORY
    _write_scaffold(target)
    (target / "custom.py").write_text("Existing implementation", encoding="utf-8")
    if missing_file:
        (target / missing_file).unlink()
    before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    command = AsyncMock(side_effect=AssertionError("Existing directories must not be scaffolded"))
    monkeypatch.setattr(scaffold_module, "run_command", command)
    phase, checkpoint_manager = _make_phase(tmp_path)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    command.assert_not_called()
    assert before == {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    checkpoint = checkpoint_manager.read()[PHASE_ID]
    assert isinstance(checkpoint, SuccessCheckpoint)
    assert checkpoint.phase_data["status"] == "existing"
    assert checkpoint.phase_data["missing_files"] == ([missing_file] if missing_file else [])
    memory = checkpoint_manager.memory_content(PHASE_ID)
    assert "Scaffold status: existing" in memory
    assert "no files were changed" in memory
    assert "preserve existing work" in memory
    if missing_file:
        assert missing_file not in checkpoint.phase_data["present_files"]
        assert f"Expected scaffold files missing: {missing_file}" in memory


@pytest.mark.parametrize(
    "result",
    [
        ToolResult(success=False, error="Scaffold command failed"),
        ToolResult(success=False, data="Scaffold command failed"),
    ],
    ids=["runner-error", "command-output"],
)
async def test_command_failure_preserves_diagnostic_without_success_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: ToolResult
):
    """A failed command must surface its diagnostic instead of handing an unusable scaffold to build."""
    monkeypatch.setattr(scaffold_module, "run_command", AsyncMock(return_value=result))
    phase, checkpoint_manager = _make_phase(tmp_path)

    with pytest.raises(RuntimeError, match="Scaffold command failed"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert checkpoint_manager.read() == {}
    assert not checkpoint_manager.memory_path(PHASE_ID).exists()


@pytest.mark.parametrize(
    ("output", "error"),
    [("absent", "expected directory"), ("partial", "incomplete"), ("symlink", "expected directory")],
)
async def test_successful_command_requires_complete_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, error: str
):
    """A zero exit status alone must not certify missing, incomplete, or redirected scaffold output."""
    target = tmp_path / DIRECTORY

    async def create(cmd: list[str], timeout: int) -> ToolResult:
        if output == "partial":
            _write_scaffold(target)
            (target / "manifest.json").unlink()
        elif output == "symlink":
            actual_directory = tmp_path / "other_integration"
            _write_scaffold(actual_directory)
            target.symlink_to(actual_directory, target_is_directory=True)
        return ToolResult(success=True)

    monkeypatch.setattr(scaffold_module, "run_command", AsyncMock(side_effect=create))
    phase, checkpoint_manager = _make_phase(tmp_path)

    with pytest.raises(RuntimeError, match=error):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert checkpoint_manager.read() == {}
    assert not checkpoint_manager.memory_path(PHASE_ID).exists()


@pytest.mark.parametrize("variables", [{}, {"integration": 42}, {"integration": "../escape"}])
async def test_invalid_input_never_runs_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variables: RuntimeVariables
):
    """Missing, mistyped, and unsafe names must be rejected before invoking the scaffold command."""
    command = AsyncMock(side_effect=AssertionError("Invalid input must not reach the command"))
    monkeypatch.setattr(scaffold_module, "run_command", command)
    phase, _ = _make_phase(tmp_path)

    with pytest.raises(ConfigError):
        await phase.execute(variables)

    command.assert_not_called()


@pytest.mark.parametrize("kind", ["file", "symlink", "dangling-symlink"])
async def test_invalid_existing_target_never_runs_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str):
    """Files and symlinks cannot be treated as reusable integration directories."""
    target = tmp_path / DIRECTORY
    if kind == "file":
        target.touch()
    else:
        destination = tmp_path / "other_integration"
        if kind == "symlink":
            destination.mkdir()
        target.symlink_to(destination, target_is_directory=True)
    command = AsyncMock(side_effect=AssertionError("Invalid targets must not reach the command"))
    monkeypatch.setattr(scaffold_module, "run_command", command)
    phase, _ = _make_phase(tmp_path)

    with pytest.raises(ConfigError, match="not a directory" if kind == "file" else "symlink"):
        await phase.execute({"integration": DISPLAY_NAME})

    command.assert_not_called()


@pytest.mark.parametrize(
    "config",
    [
        PhaseConfig(name=PHASE_ID, agent="builder"),
        PhaseConfig(name=PHASE_ID, tasks=[TaskConfig(name="scaffold", prompt="Create a scaffold")]),
        PhaseConfig(name=PHASE_ID, checkpoint=CheckpointConfig(memory_prompt="Summarize")),
    ],
    ids=["agent", "tasks", "memory-prompt"],
)
def test_agentic_configuration_is_rejected(config: PhaseConfig):
    """Agentic settings must fail validation rather than silently being ignored by this deterministic phase."""
    with pytest.raises(ConfigError, match="does not accept"):
        ApiScaffoldPhase.validate_config(PHASE_ID, config)
