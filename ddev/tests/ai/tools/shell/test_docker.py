# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ddev.ai.tools.shell.docker import DockerTool


@pytest.mark.parametrize("explicit_cwd", [False, True])
async def test_docker_executes_literal_arguments_in_requested_directory(tmp_path: Path, explicit_cwd: bool):
    cwd = str(tmp_path / "compose project") if explicit_cwd else None
    args = ["compose", "--file", "compose file.yaml", "config", "$(echo unsafe); echo unsafe", "*"]
    raw: dict[str, object] = {"args": args}
    if explicit_cwd:
        raw["cwd"] = cwd

    proc = MagicMock(returncode=0)
    proc.communicate = AsyncMock(return_value=(b"", b""))
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)) as create_process:
        await DockerTool().run(raw)

    create_process.assert_awaited_once_with(
        "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
    )
