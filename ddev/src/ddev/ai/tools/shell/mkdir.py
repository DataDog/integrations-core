# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput

from .base import CmdTool


class MkdirInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the directory to create")]


class MkdirTool(CmdTool[MkdirInput]):
    """Creates a directory at the given path, including any missing parent directories.
    Use to create directories for config files, logs, source code."""

    timeout = 5

    @property
    def name(self) -> str:
        return "mkdir"

    def cmd(self, tool_input: MkdirInput) -> list[str]:
        return ["mkdir", "-p", tool_input.path]
