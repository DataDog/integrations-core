# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.tools.fs.append_file import AppendFileTool
from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.edit_file import EditFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.read_file import ReadFileTool


async def test_workflow_create_read_edit_append(
    create_tool: CreateFileTool,
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    append_tool: AppendFileTool,
    registry: FileRegistry,
    tmp_path,
) -> None:
    f = tmp_path / "workflow.txt"

    # Step 1: create
    r = await create_tool.run({"path": str(f), "content": "version: 1\n"})
    assert r.success is True

    # Step 2: read (registers current content)
    r = await read_tool.run({"path": str(f)})
    assert r.success is True

    # Step 3: edit
    r = await edit_tool.run({"path": str(f), "old_string": "version: 1", "new_string": "version: 2"})
    assert r.success is True
    assert "version: 2" in f.read_text(encoding="utf-8")

    # Step 4: append
    r = await append_tool.run({"path": str(f), "content": "# updated\n"})
    assert r.success is True
    assert f.read_text(encoding="utf-8").endswith("# updated\n")

    # Registry must reflect the final state
    assert registry.verify(str(f), f.read_text(encoding="utf-8")) is True


async def test_workflow_stale_file(
    create_tool: CreateFileTool,
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    tmp_path,
) -> None:
    f = tmp_path / "shared.txt"
    await create_tool.run({"path": str(f), "content": "original\n"})
    f.write_text("updated externally\n", encoding="utf-8")

    result = await edit_tool.run({"path": str(f), "old_string": "original", "new_string": "my edit"})
    assert result.success is False
    assert "Re-read and retry" in result.error

    await read_tool.run({"path": str(f)})

    result = await edit_tool.run({"path": str(f), "old_string": "updated externally", "new_string": "final"})
    assert result.success is True
    assert f.read_text(encoding="utf-8") == "final\n"
