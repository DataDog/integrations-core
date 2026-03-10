# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .base import safe_int
from .cmd import CmdTool
from .types import ToolResult


class ReadFileTool(CmdTool):
    """Tool for reading files."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Reads contents of a text file from the host filesystem. "
            "Use to inspect config files, logs, source code. "
            "Do not use for binary files. "
            "Supports offset/limit for paging through large files."
        )

    @property
    def input_schema(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-indexed, default: 0)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of lines to read (default: all remaining lines)",
                },
            },
            "required": ["path"],
        }

    def cmd(self, tool_input: dict[str, object]) -> list[str]:
        path = str(tool_input["path"])
        offset = safe_int(tool_input.get("offset"), 0)
        limit = safe_int(tool_input.get("limit"), None)
        if offset == 0 and limit is None:
            return ["cat", path]
        start = offset + 1
        if limit is not None:
            return ["awk", f"NR>={start} && NR<={start + limit - 1}", path]
        return ["awk", f"NR>={start}", path]

    async def __call__(self, tool_input: dict[str, object]) -> ToolResult:
        if not tool_input.get("path"):
            return ToolResult(success=False, error="Missing required parameter: path")
        return await super().__call__(tool_input)
