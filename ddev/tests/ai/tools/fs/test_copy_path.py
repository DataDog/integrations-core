# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

from ddev.ai.tools.fs.copy_path import CopyPathTool
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


def test_tool_name(copy_tool: CopyPathTool) -> None:
    assert copy_tool.name == "copy_path"


async def test_copy_file_success(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_bytes(b"hello world")

    result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is True
    assert dst.read_bytes() == b"hello world"
    assert str(dst) in result.data
    assert "11" in result.data  # byte count


async def test_copy_directory_success(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "sub").mkdir()
    (src / "sub" / "b.txt").write_text("b", encoding="utf-8")
    dst = tmp_path / "dst_dir"

    result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is True
    assert (dst / "a.txt").read_text(encoding="utf-8") == "a"
    assert (dst / "sub" / "b.txt").read_text(encoding="utf-8") == "b"
    assert "2" in result.data  # file count


async def test_copy_file_creates_missing_parent_dirs(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("content", encoding="utf-8")
    dst = tmp_path / "a" / "b" / "c" / "dst.txt"

    result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is True
    assert dst.exists()
    assert dst.read_text(encoding="utf-8") == "content"


async def test_copy_directory_merges_with_existing_destination(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "new.txt").write_text("new", encoding="utf-8")

    dst = tmp_path / "dst_dir"
    dst.mkdir()
    (dst / "existing.txt").write_text("existing", encoding="utf-8")

    result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is True
    assert (dst / "new.txt").read_text(encoding="utf-8") == "new"
    assert (dst / "existing.txt").read_text(encoding="utf-8") == "existing"


async def test_copy_source_not_found(copy_tool: CopyPathTool, tmp_path) -> None:
    result = await copy_tool.run({"source": str(tmp_path / "missing.txt"), "destination": str(tmp_path / "dst.txt")})

    assert result.success is False
    assert "does not exist" in result.error


async def test_copy_file_oserror(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path / "dst"

    with patch("ddev.ai.tools.fs.copy_path.shutil.copy2", side_effect=OSError("permission denied")):
        result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is False
    assert result.error is not None


async def test_copy_directory_oserror(copy_tool: CopyPathTool, tmp_path) -> None:
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "f.txt").write_text("data", encoding="utf-8")
    dst = tmp_path / "dst"

    with patch("ddev.ai.tools.fs.copy_path.shutil.copytree", side_effect=OSError("permission denied")):
        result = await copy_tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is False
    assert result.error is not None


async def test_copy_write_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    tool = CopyPathTool(policy)

    src = tmp_path / "src.txt"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path.parent / "outside_write_root.txt"

    result = await tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is False
    assert result.error is not None


async def test_copy_read_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=("*.secret",))
    tool = CopyPathTool(policy)

    src = tmp_path.parent / "credentials.secret"
    dst = tmp_path / "dst.txt"

    result = await tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is False
    assert result.error is not None


async def test_copy_directory_denied_child_is_rejected(tmp_path) -> None:
    # write_root is a subdirectory; src lives outside it so deny patterns apply to its contents.
    write_root = tmp_path / "write_root"
    write_root.mkdir()
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(".env",))
    tool = CopyPathTool(policy)

    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "safe.txt").write_text("ok", encoding="utf-8")
    (src / ".env").write_text("SECRET=hunter2", encoding="utf-8")
    dst = write_root / "dst_dir"

    result = await tool.run({"source": str(src), "destination": str(dst)})

    assert result.success is False
    assert result.error is not None
    assert not dst.exists()
