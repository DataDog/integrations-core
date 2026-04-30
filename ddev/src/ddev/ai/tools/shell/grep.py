# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessError, FileAccessPolicy, canonicalize_path

from .base import CmdTool, run_command


class GrepInput(BaseToolInput):
    pattern: Annotated[str, Field(description="Regex pattern to search for")]
    path: Annotated[str, Field(description="File or directory to search in")]
    recursive: Annotated[bool, Field(description="Search recursively in directories (default: true)")] = True


class GrepTool(CmdTool[GrepInput]):
    """Searches for a regex pattern in files. Returns matching lines with file path and line
    numbers. Use to find specific config values, ports, hostnames across files. Supports extended
    regex syntax. Output might be truncated for large results.
    """

    timeout = 30

    def __init__(self, policy: FileAccessPolicy) -> None:
        self._policy = policy

    @property
    def name(self) -> str:
        return "grep"

    async def __call__(self, tool_input: GrepInput) -> ToolResult:
        try:
            self._policy.assert_readable(tool_input.path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))
        result = await run_command(
            self.cmd(tool_input),
            timeout=self.timeout,
            stdout_filter=self._filter_stdout if tool_input.recursive else None,
        )
        # grep exits 1 when no lines match — not a failure
        if not result.success and result.error is None:
            return result.model_copy(update={"success": True})
        return result

    def cmd(self, tool_input: GrepInput) -> list[str]:
        cmd = ["grep", "-n", "-E", "--null", "-I", "--no-messages"]
        if tool_input.recursive:
            cmd.append("-r")
            cmd.extend(self._exclude_flags(canonicalize_path(tool_input.path)))
        cmd += ["--", tool_input.pattern, tool_input.path]
        return cmd

    def _exclude_flags(self, search_path: Path) -> list[str]:
        # Skip --exclude= flags when the search overlaps write_root: either the
        # search is inside write_root (all files are visible) or write_root is
        # inside the search (mixing zones). In both cases the post-filter handles
        # per-line decisions correctly. Only apply flags when the entire search
        # is outside write_root, where deny patterns are fully in effect.
        write_root = self._policy.write_root
        if search_path.is_relative_to(write_root) or write_root.is_relative_to(search_path):
            return []
        return [f"--exclude={pat}" for pat in self._policy.basename_patterns]

    def _filter_stdout(self, stdout: str) -> str:
        """Filter stdout to only include lines whose filename is allowed by the policy.
        If the filename is denied, we return 'Read denied by policy' instead of the line.

        ``grep --null`` output: ``<filename>\\0<lineno>:<content>\\n``. Split on the
        first NUL and run the filename through ``assert_readable`` (which
        canonicalizes through symlinks).

        Only use when recursive is True.
        """
        decision: dict[str, bool] = {}
        result: list[str] = []
        emitted_denials: set[str] = set()
        for line in stdout.splitlines():
            nul = line.find("\0")
            if nul == -1:
                continue
            filename, rest = line[:nul], line[nul + 1 :]
            allowed = decision.get(filename)
            if allowed is None:
                try:
                    self._policy.assert_readable(filename)
                    allowed = True
                except FileAccessError:
                    allowed = False
                decision[filename] = allowed
            if allowed:
                result.append(f"{filename}:{rest}")
            elif filename not in emitted_denials:
                result.append(f"{filename}: Read denied by policy")
                emitted_denials.add(filename)
        return "\n".join(result)
