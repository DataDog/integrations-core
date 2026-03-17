# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from dataclasses import dataclass
from typing import Annotated

import pytest

from ddev.ai.tools.core.base import BaseTool, _get_input_type, _resolve_json_type, build_schema, safe_int
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Minimal concrete tools used across tests
# ---------------------------------------------------------------------------


@dataclass
class SimpleInput:
    message: Annotated[str, "A message to echo"]


@dataclass
class FullInput:
    required_str: Annotated[str, "A required string"]
    optional_int: Annotated[int | None, "An optional integer"] = None
    flag: Annotated[bool, "A boolean flag"] = False


class EchoTool(BaseTool[SimpleInput]):
    """Echo the message back."""

    @property
    def name(self) -> str:
        return "echo"

    async def __call__(self, tool_input: SimpleInput) -> ToolResult:
        return ToolResult(success=True, data=tool_input.message)


class FailingTool(BaseTool[SimpleInput]):
    """A tool that always raises."""

    @property
    def name(self) -> str:
        return "failing"

    async def __call__(self, tool_input: SimpleInput) -> ToolResult:
        raise RuntimeError("something went wrong")


class FullInputTool(BaseTool[FullInput]):
    """Tool using FullInput."""

    @property
    def name(self) -> str:
        return "full"

    async def __call__(self, tool_input: FullInput) -> ToolResult:
        return ToolResult(success=True)


# ---------------------------------------------------------------------------
# safe_int
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (5, 5),
        (3.7, 3),
        ("42", 42),
        ("0", 0),
        ("-7", -7),
    ],
)
def test_safe_int_valid_conversions(value, expected):
    assert safe_int(value, default=0) == expected


@pytest.mark.parametrize("value", ["abc", "3.5", "", None, [], {}])
def test_safe_int_default(value):
    assert safe_int(value, default=-1) == -1


def test_safe_int_none_default():
    assert safe_int("bad", default=None) is None
    assert safe_int("bad") == 0
    assert safe_int([1]) == 0


# ---------------------------------------------------------------------------
# _resolve_json_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hint,expected",
    [
        (str, "string"),
        (int, "integer"),
        (float, "number"),
        (bool, "boolean"),
    ],
)
def test_resolve_json_type_primitives(hint, expected):
    assert _resolve_json_type(hint) == expected


def test_resolve_json_type_unknown_type():
    assert _resolve_json_type(list) is None
    assert _resolve_json_type(dict) is None
    assert _resolve_json_type(str | int) is None


def test_resolve_json_type_optional_type():
    assert _resolve_json_type(str | None) == "string"
    assert _resolve_json_type(int | None) == "integer"


# ---------------------------------------------------------------------------
# build_schema
# ---------------------------------------------------------------------------


def test_build_schema_simple_input():
    schema = build_schema(SimpleInput)

    assert schema["type"] == "object"
    assert schema["required"] == ["message"]
    assert schema["properties"]["message"]["description"] == "A message to echo"
    assert schema["properties"]["message"]["type"] == "string"


def test_build_schema_full_input():
    schema = build_schema(FullInput)

    assert "optional_int" not in schema.get("required", [])
    assert "flag" not in schema.get("required", [])
    assert "required_str" in schema["required"]
    assert schema["properties"]["flag"]["type"] == "boolean"


def test_build_schema_all_optional():
    @dataclass
    class AllOptional:
        x: Annotated[str, "x"] = "default"
        y: Annotated[int, "y"] = 0

    schema = build_schema(AllOptional)
    assert "required" not in schema


def test_build_schema_bad_input():
    @dataclass
    class BadInput:
        field: Annotated[str | int, "ambiguous"]

    with pytest.raises(TypeError, match="BadInput.field"):
        build_schema(BadInput)


# ---------------------------------------------------------------------------
# _get_input_type
# ---------------------------------------------------------------------------


def test_get_input_type_returns_correct_input_type():
    class ChildTool(EchoTool):
        pass

    assert _get_input_type(EchoTool) is SimpleInput
    assert _get_input_type(FullInputTool) is FullInput
    assert _get_input_type(ChildTool) is SimpleInput


def test_get_input_type_unparameterized_subclass():
    # A class that extends BaseTool without a type argument cannot be resolved
    class BareSubclass(BaseTool):  # type: ignore[type-arg]
        @property
        def name(self) -> str:
            return "bare"

        async def __call__(self, tool_input) -> ToolResult:  # type: ignore[override]
            return ToolResult(success=True)

    with pytest.raises(TypeError, match="BareSubclass"):
        _get_input_type(BareSubclass)


def test_resolves_through_intermediate_generic():
    # Simulates the CmdTool[TInput] -> BaseTool[TInput] pattern
    class IntermediateTool[T](BaseTool[T]):
        @property
        def name(self) -> str:
            return "intermediate"

        async def __call__(self, tool_input: T) -> ToolResult:  # type: ignore[override]
            return ToolResult(success=True)

    class ConcreteTool(IntermediateTool[SimpleInput]):
        pass

    assert _get_input_type(ConcreteTool) is SimpleInput


# ---------------------------------------------------------------------------
# BaseTool
# ---------------------------------------------------------------------------


@pytest.fixture
def echo_tool() -> EchoTool:
    return EchoTool()


@pytest.fixture
def failing_tool() -> FailingTool:
    return FailingTool()


def test_build_tool(echo_tool: EchoTool):
    assert echo_tool.name == "echo"
    assert echo_tool.description == "Echo the message back."
    assert echo_tool.input_schema == build_schema(SimpleInput)
    assert echo_tool.definition == {
        "name": "echo",
        "description": "Echo the message back.",
        "input_schema": build_schema(SimpleInput),
    }


def test_build_tool_no_docstring():
    class NoDocstringTool(BaseTool[SimpleInput]):
        @property
        def name(self) -> str:
            return "nodoc"

        async def __call__(self, tool_input: SimpleInput) -> ToolResult:
            return ToolResult(success=True)

    assert NoDocstringTool().description == ""


def test_cannot_instantiate_abstract_base_directly():
    with pytest.raises(TypeError):
        BaseTool()  # type: ignore[abstract]


# --- run(): happy path ---


def test_run_valid_input_returns_success(echo_tool: EchoTool):
    result = asyncio.run(echo_tool.run({"message": "hello"}))
    assert result.success is True
    assert result.data == "hello"


# --- run(): input validation failures ---


def test_run_missing_required_field_returns_failure(echo_tool: EchoTool):
    result = asyncio.run(echo_tool.run({}))
    assert result.success is False
    assert result.error is not None


def test_run_unexpected_extra_field_returns_failure(echo_tool: EchoTool):
    result = asyncio.run(echo_tool.run({"message": "hi", "extra": "oops"}))
    assert result.success is False


# --- run(): __call__ exception handling ---


def test_run_captures_exception_from_call(failing_tool: FailingTool):
    result = asyncio.run(failing_tool.run({"message": "boom"}))
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "RuntimeError" in result.error
    assert "something went wrong" in result.error
