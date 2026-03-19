# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import inspect
import typing
from abc import ABC, abstractmethod
from types import get_original_bases
from typing import Any

from anthropic.types import ToolParam
from pydantic import BaseModel, ConfigDict

from .types import ToolResult


class BaseToolInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @classmethod
    def to_input_schema(cls) -> dict[str, object]:
        schema = cls.model_json_schema()
        schema.pop('title', None)
        for prop in schema.get('properties', {}).values():
            prop.pop('title', None)
            prop.pop('default', None)
            if 'anyOf' in prop:
                non_null = [t for t in prop['anyOf'] if t != {'type': 'null'}]
                if len(non_null) == 1:
                    prop.update(non_null[0])
                    del prop['anyOf']
        return schema


def _get_input_type(cls: type) -> type[BaseToolInput]:
    """Extract the TInput type from a BaseTool subclass"""
    if resolved := _resolve_base_tool_arg(cls, {}):
        return resolved
    raise TypeError(f"{cls.__name__} must be parameterized with an input type: class MyTool(BaseTool[MyInput])")


def _resolve_base_tool_arg(cls: type, type_map: dict[Any, Any]) -> type[BaseToolInput] | None:
    """Resolve the TInput type from a BaseTool subclass, resolving through intermediate generics."""
    for base in get_original_bases(cls):
        origin = typing.get_origin(base) or base
        args = typing.get_args(base)

        if origin is BaseTool and args:
            resolved = type_map.get(args[0], args[0])
            if isinstance(resolved, type):
                return resolved
        elif isinstance(origin, type) and issubclass(origin, BaseTool) and origin is not BaseTool:
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
            if resolved := _resolve_base_tool_arg(origin, new_map):
                return resolved

    return None


class BaseTool[TInput: BaseToolInput](ABC):
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
        return _get_input_type(type(self)).to_input_schema()

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
            input_cls = _get_input_type(type(self))
            validated: TInput = input_cls.model_validate(raw)  # type: ignore[assignment]
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
