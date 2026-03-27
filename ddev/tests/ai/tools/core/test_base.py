# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

import pytest
from pydantic import Field

from ddev.ai.tools.core.base import BaseTool, BaseToolInput, _get_input_type
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Minimal concrete tools used across tests
# ---------------------------------------------------------------------------


class SimpleInput(BaseToolInput):
    message: Annotated[str, Field(description="A message to echo")]


class FullInput(BaseToolInput):
    required_str: Annotated[str, Field(description="A required string")]
    optional_int: Annotated[int | None, Field(description="An optional integer")] = None
    flag: Annotated[bool, Field(description="A boolean flag")] = False


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
# BaseToolInput.to_input_schema()
# ---------------------------------------------------------------------------


def test_to_input_schema_type_and_required():
    schema = SimpleInput.to_input_schema()
    assert schema["type"] == "object"
    assert schema["required"] == ["message"]


def test_to_input_schema_field_description():
    schema = SimpleInput.to_input_schema()
    assert schema["properties"]["message"]["description"] == "A message to echo"
    assert schema["properties"]["message"]["type"] == "string"


def test_to_input_schema_no_title_keys():
    schema = FullInput.to_input_schema()
    assert "title" not in schema
    for prop in schema["properties"].values():
        assert "title" not in prop


def test_to_input_schema_additional_properties_false():
    assert SimpleInput.to_input_schema().get("additionalProperties") is False


def test_to_input_schema_optional_fields_not_required():
    schema = FullInput.to_input_schema()
    assert "required_str" in schema["required"]
    assert "optional_int" not in schema["required"]
    assert "flag" not in schema["required"]


def test_to_input_schema_anyof_flattened_for_optional_int():
    schema = FullInput.to_input_schema()
    prop = schema["properties"]["optional_int"]
    assert "anyOf" not in prop
    assert prop["type"] == "integer"


def test_to_input_schema_all_optional_no_required_key():
    class AllOptional(BaseToolInput):
        x: Annotated[str, Field(description="x")] = "default"
        y: Annotated[int, Field(description="y")] = 0

    schema = AllOptional.to_input_schema()
    assert "required" not in schema


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
    assert echo_tool.input_schema == SimpleInput.to_input_schema()
    assert echo_tool.definition == {
        "name": "echo",
        "description": "Echo the message back.",
        "input_schema": SimpleInput.to_input_schema(),
    }


def test_build_tool_no_docstring():
    class NoDocstringTool(BaseTool[SimpleInput]):
        @property
        def name(self) -> str:
            return "nodoc"

        async def __call__(self, tool_input: SimpleInput) -> ToolResult:
            return ToolResult(success=True)

    assert NoDocstringTool().description == ""


# --- run(): happy path ---


async def test_run_valid_input_returns_success(echo_tool: EchoTool):
    result = await echo_tool.run({"message": "hello"})
    assert result.success is True
    assert result.data == "hello"


# --- run(): input validation failures ---


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"message": "hi", "extra": "oops"},
    ],
)
async def test_run_invalid_input_returns_failure(echo_tool: EchoTool, raw: dict):
    result = await echo_tool.run(raw)
    assert result.success is False
    assert result.error is not None


# --- run(): __call__ exception handling ---


async def test_run_captures_exception_from_call(failing_tool: FailingTool):
    result = await failing_tool.run({"message": "boom"})
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "RuntimeError" in result.error
    assert "something went wrong" in result.error
