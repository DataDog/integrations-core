# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import dataclasses
import inspect
import types as _types
import typing
from abc import ABC, abstractmethod
from types import get_original_bases
from typing import Annotated, Any, get_args, get_type_hints, overload

from anthropic.types import ToolParam

from .types import ToolResult

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
        if json_type is None:
            supported = ", ".join(t.__name__ for t in _JSON_TYPE_MAP)
            raise TypeError(
                f"{cls.__name__}.{field_name}: type {raw_type!r} cannot be mapped to a JSON Schema type. "
                f"Supported types are: {supported}, and Optional variants."
            )
        prop["type"] = json_type

        properties[field_name] = prop

        field = fields.get(field_name)
        if field and field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            required.append(field_name)

    schema: dict[str, object] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _get_input_type(cls: type) -> type:
    """Extract the TInput type from a BaseTool subclass, resolving through intermediate generics."""
    if resolved := _resolve_base_tool_arg(cls, {}):
        return resolved
    raise TypeError(f"{cls.__name__} must be parameterized with an input type: class MyTool(BaseTool[MyInput])")


def _resolve_base_tool_arg(cls: type, type_map: dict) -> type | None:
    for base in get_original_bases(cls):
        origin = typing.get_origin(base) or base
        args = typing.get_args(base)

        if origin is BaseTool and args:
            resolved = type_map.get(args[0], args[0])
            if isinstance(resolved, type):
                return resolved

        if isinstance(origin, type) and issubclass(origin, BaseTool) and origin is not BaseTool:
            # Call recursively until we find the generic type of the first BaseTool ancestor.
            # Example:
            # class EchoTool(BaseTool[EchoInput]):
            #     pass
            # class ChildTool[T](EchoTool):
            #     pass
            # class ConcreteChildTool(ChildTool[int]):
            #     pass
            # _get_input_type(ConcreteChildTool) will resolve to EchoInput.
            type_params = origin.__type_params__
            new_map = {param: type_map.get(arg, arg) for param, arg in zip(type_params, args, strict=False)}
            try:
                return _resolve_base_tool_arg(origin, new_map)
            except TypeError:
                continue

    raise TypeError


class BaseTool[TInput](ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in API calls."""
        ...

    @property
    def description(self) -> str:
        return inspect.cleandoc(self.__class__.__doc__) if self.__class__.__doc__ else ""

    @property
    def input_schema(self) -> dict[str, object]:
        return build_schema(_get_input_type(type(self)))

    @property
    def definition(self) -> ToolParam:
        """Build the Anthropic SDK ToolParam from this tool's metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    async def run(self, raw: dict[str, object]) -> ToolResult:
        """Coerce raw dict to the typed Input class and delegate to __call__."""
        try:
            validated = _get_input_type(type(self))(**raw)
        except (TypeError, ValueError) as e:
            return ToolResult(success=False, error=str(e))
        try:
            return await self(validated)
        except Exception as e:
            return ToolResult(success=False, error=f"{type(e).__name__}: {str(e)}")

    @abstractmethod
    async def __call__(self, tool_input: TInput) -> ToolResult:
        """Call the tool with a typed input instance."""
        ...
