# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import dataclasses
import inspect
import typing
from abc import ABC, abstractmethod
from typing import Annotated, Any, ClassVar, get_args, get_type_hints, overload

from anthropic.types import ToolParam

from .types import ToolResult

ALLOWED_TOOL_CALLERS = ["code_execution_20260120"]

_JSON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


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


def _resolve_json_type(hint: Any) -> str | None:
    import types as _types

    origin = typing.get_origin(hint)
    if origin is typing.Union or isinstance(hint, _types.UnionType):
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(args) == 1:
            return _resolve_json_type(args[0])
        return None
    return _JSON_TYPE_MAP.get(hint)


def build_schema(cls: type) -> dict[str, object]:
    """Build a JSON schema dict from an Annotated dataclass."""
    hints = get_type_hints(cls, include_extras=True)
    fields = {f.name: f for f in dataclasses.fields(cls)}

    properties: dict[str, object] = {}
    required: list[str] = []

    for field_name, hint in hints.items():
        prop: dict[str, object] = {}

        if typing.get_origin(hint) is Annotated:
            args = get_args(hint)
            raw_type = args[0]
            description = next((a for a in args[1:] if isinstance(a, str)), None)
            if description:
                prop["description"] = description
        else:
            raw_type = hint

        json_type = _resolve_json_type(raw_type)
        if json_type:
            prop["type"] = json_type

        properties[field_name] = prop

        field = fields.get(field_name)
        if field and field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            required.append(field_name)

    schema: dict[str, object] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


class ToolProtocol(typing.Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def definition(self) -> ToolParam: ...
    async def run(self, raw: dict[str, object]) -> ToolResult: ...
    async def __call__(self, tool_input: Any) -> ToolResult: ...


class BaseTool(ABC, ToolProtocol):
    Input: ClassVar[type]

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in API calls."""
        ...

    @property
    def description(self) -> str:
        return inspect.getdoc(self.__class__) or ""

    @property
    def input_schema(self) -> dict[str, object]:
        return build_schema(self.Input)

    @property
    def definition(self) -> ToolParam:
        """Build the Anthropic SDK ToolParam from this tool's metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "allowed_callers": ALLOWED_TOOL_CALLERS,
        }

    async def run(self, raw: dict[str, object]) -> ToolResult:
        """Coerce raw dict to the typed Input class and delegate to __call__."""
        try:
            validated = self.Input(**raw)
        except TypeError as e:
            return ToolResult(success=False, error=str(e))
        return await self(validated)

    @abstractmethod
    async def __call__(self, tool_input: Any) -> ToolResult:
        """Call the tool with a typed input instance."""
        ...
