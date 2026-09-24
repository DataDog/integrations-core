# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest.mock import patch

import pytest

from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.delete_file import DeleteFileTool
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry


@pytest.fixture
def permissive_policy(tmp_path) -> FileAccessPolicy:
    """Overrides the base fixture with an integration_name, so integration_root resolves."""
    return FileAccessPolicy(write_root=tmp_path, deny_patterns=(), integration_name="My Integration")


@pytest.fixture
async def known_file_in_root(create_tool: CreateFileTool, integration_root: Path) -> Path:
    f = integration_root / "check.py"
    await create_tool.run({"path": str(f), "content": "print('hi')\n"})
    return f


def test_tool_name(registry: FileRegistry, owner_id: str):
    assert DeleteFileTool(registry, owner_id).name == "delete_file"


async def test_delete_file_success(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, known_file_in_root: Path
):
    result = await delete_tool.run({"path": str(known_file_in_root)})

    assert result.success is True
    assert not known_file_in_root.exists()
    assert registry.is_known(owner_id, str(known_file_in_root)) is False


@pytest.mark.parametrize("use_dotdot_escape", [False, True])
async def test_delete_file_refuses_outside_integration_root(
    delete_tool: DeleteFileTool,
    registry: FileRegistry,
    owner_id: str,
    integration_root: Path,
    tmp_path: Path,
    use_dotdot_escape: bool,
):
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    registry.record(owner_id, str(outside), "x")
    path = str(integration_root / ".." / "outside.txt") if use_dotdot_escape else str(outside)

    result = await delete_tool.run({"path": path})

    assert result.success is False
    assert "outside the integration directory" in result.error
    assert outside.exists()


async def test_delete_file_refuses_symlinked_parent_escape(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, integration_root: Path, tmp_path: Path
):
    outside = tmp_path / "outside_dir"
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("x", encoding="utf-8")
    registry.record(owner_id, str(target), "x")

    link = integration_root / "linked"
    link.symlink_to(outside)

    result = await delete_tool.run({"path": str(link / "secret.txt")})

    assert result.success is False
    assert "outside the integration directory" in result.error
    assert target.exists()


async def test_delete_file_refuses_directory(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, integration_root: Path
):
    d = integration_root / "subdir"
    d.mkdir()
    registry.record(owner_id, str(d), "")

    result = await delete_tool.run({"path": str(d)})

    assert result.success is False
    assert "is a directory" in result.error
    assert d.exists()


async def test_delete_file_refuses_symlink_to_file(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, integration_root: Path, known_file_in_root: Path
):
    link = integration_root / "link.py"
    link.symlink_to(known_file_in_root)
    registry.record(owner_id, str(link), "")

    result = await delete_tool.run({"path": str(link)})

    assert result.success is False
    assert "is a symlink" in result.error
    assert link.exists()
    assert known_file_in_root.exists()


async def test_delete_file_refuses_unknown_file(delete_tool: DeleteFileTool, integration_root: Path):
    f = integration_root / "untracked.py"
    f.write_text("x", encoding="utf-8")

    result = await delete_tool.run({"path": str(f)})

    assert result.success is False
    assert "Not authorized" in result.error
    assert f.exists()


async def test_delete_file_refuses_file_only_another_owner_read(
    delete_tool: DeleteFileTool, registry: FileRegistry, integration_root: Path
):
    f = integration_root / "shared.py"
    f.write_text("x", encoding="utf-8")
    registry.record("other-agent", str(f), "x")

    result = await delete_tool.run({"path": str(f)})

    assert result.success is False
    assert "Not authorized" in result.error
    assert f.exists()


async def test_delete_file_refuses_stale_content(delete_tool: DeleteFileTool, known_file_in_root: Path):
    """The registry's is_known check alone doesn't catch a file changed since it was last
    read or created; the current content must be verified before it is destroyed."""
    known_file_in_root.write_text("changed externally\n", encoding="utf-8")

    result = await delete_tool.run({"path": str(known_file_in_root)})

    assert result.success is False
    assert "Re-read and retry" in result.error
    assert known_file_in_root.exists()


@pytest.mark.parametrize(
    "relative",
    [
        "manifest.json",
        "pyproject.toml",
        "hatch.toml",
        "metadata.csv",
        "README.md",
        "assets/configuration/spec.yaml",
        "datadog_checks/mycheck/config_models/defaults.py",
        "datadog_checks/mycheck/data/conf.yaml.example",
    ],
)
async def test_delete_file_refuses_protected_structural_paths(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, integration_root: Path, relative: str
):
    f = integration_root / relative
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    registry.record(owner_id, str(f), "x")

    result = await delete_tool.run({"path": str(f)})

    assert result.success is False
    assert "protected structural file" in result.error
    assert f.exists()


@pytest.mark.parametrize("filename", [".env", "secret.pem", "private.key"])
async def test_delete_file_refuses_deny_pattern_files(owner_id: str, tmp_path: Path, filename: str):
    # Deny patterns must be enforced even inside write_root/integration_root, unlike
    # ordinary writes, so this uses the default deny patterns rather than the
    # `permissive_policy` fixture (which disables them for the other tests in this module).
    registry = FileRegistry(policy=FileAccessPolicy(write_root=tmp_path, integration_name="My Integration"))
    integration_root = registry.policy._integration_root
    integration_root.mkdir()
    tool = DeleteFileTool(registry, owner_id)

    f = integration_root / filename
    f.write_text("secret", encoding="utf-8")
    registry.record(owner_id, str(f), "secret")

    result = await tool.run({"path": str(f)})

    assert result.success is False
    assert "Delete denied by policy" in result.error
    assert f.exists()


async def test_delete_file_missing_path_is_an_error(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, integration_root: Path
):
    f = integration_root / "gone.py"
    registry.record(owner_id, str(f), "x")

    result = await delete_tool.run({"path": str(f)})

    assert result.success is False
    assert "No such file" in result.error


async def test_delete_file_oserror_on_unlink(
    delete_tool: DeleteFileTool, registry: FileRegistry, owner_id: str, known_file_in_root: Path
):
    with patch("pathlib.Path.unlink", side_effect=PermissionError("permission denied")):
        result = await delete_tool.run({"path": str(known_file_in_root)})

    assert result.success is False
    assert result.error is not None
    assert registry.is_known(owner_id, str(known_file_in_root)) is True
