# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod
from typing import overload

from anthropic.types import ToolParam

from ddev.cli.meta.auto_build.constants import ALLOWED_TOOL_CALLERS

from .types import ToolResult


@overload
def safe_int(value: object, default: int) -> int: ...
@overload
def safe_int(value: object, default: None) -> int | None: ...
def safe_int(value: object, default: int | None = 0) -> int | None:
    """Safely convert an object value (from JSON) to int."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class BaseTool(ABC):
    # add docstring

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in API calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """A short description of the tool that will be sent to the LLM."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, object]:
        """JSON schema of the input parameters for the tool."""
        ...

    @property
    def definition(self) -> ToolParam:
        """Build the Anthropic SDK ToolParam from this tool's metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "allowed_callers": ALLOWED_TOOL_CALLERS,
        }

    @abstractmethod
    async def __call__(self, tool_input: dict[str, object]) -> ToolResult:
        """Call the tool with the given input."""
        ...
