# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared fixtures for ddev.ai tests: a fake tool double for building real ToolRegistry instances.

Not meant to be imported directly by test modules — use the `fake_tool` fixture instead of
reaching into this file. Importing FakeTool/FakeToolFactory under `if TYPE_CHECKING:` purely
for parameter annotations is fine; nothing here should be imported at runtime.
"""

from typing import Protocol

import pytest

from ddev.ai.tools.core.types import ToolResult


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


class FakeToolFactory(Protocol):
    """Callable signature of the `fake_tool` fixture."""

    def __call__(
        self,
        name: str = "fake_tool",
        result: ToolResult | None = None,
        error: BaseException | None = None,
        truncated_call_hint: str | None = None,
    ) -> FakeTool: ...


@pytest.fixture
def fake_tool() -> FakeToolFactory:
    """Factory fixture: fake_tool(name="fake_tool", result=None, error=None, truncated_call_hint=None).

    All arguments are optional, so `fake_tool()` alone produces a usable, successful tool double.
    Build a real ToolRegistry directly from one or more of these: ToolRegistry([fake_tool("x")]).
    """

    def _make(
        name: str = "fake_tool",
        result: ToolResult | None = None,
        error: BaseException | None = None,
        truncated_call_hint: str | None = None,
    ) -> FakeTool:
        return FakeTool(name, result=result, error=error, truncated_call_hint=truncated_call_hint)

    return _make
