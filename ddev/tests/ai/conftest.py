# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared fixtures for ddev.ai tests: a fake tool double and a real ToolRegistry factory.

Not meant to be imported directly by test modules — use the `fake_tool` and `tool_registry`
fixtures instead of reaching into this file.
"""

import pytest

from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry


class FakeTool:
    """ToolProtocol double with a configurable result, error, and truncated_call_hint.
    Obtained via the `fake_tool` fixture, never constructed directly by test modules."""

    def __init__(
        self,
        name: str,
        result: ToolResult | None = None,
        error: BaseException | None = None,
        truncated_call_hint: str | None = None,
    ) -> None:
        self._name = name
        self._result = result if result is not None else ToolResult(success=True, data=f"{name} ok")
        self._error = error
        self.truncated_call_hint = truncated_call_hint
        self.calls: list[dict[str, object]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fake tool {self._name}"

    @property
    def definition(self) -> dict[str, object]:
        return {"name": self._name, "description": self.description, "input_schema": {}}

    async def run(self, raw: dict[str, object]) -> ToolResult:
        self.calls.append(raw)
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture
def fake_tool():
    """Factory fixture: fake_tool(name, result=None, error=None, truncated_call_hint=None) -> FakeTool."""
    return FakeTool


@pytest.fixture
def tool_registry():
    """Factory fixture: tool_registry(*tools) -> a real ToolRegistry built from the given tools."""

    def _make(*tools: object) -> ToolRegistry:
        return ToolRegistry(list(tools))

    return _make
