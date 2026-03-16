# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from dataclasses import dataclass
from typing import Annotated

import pytest

from ddev.ai.tools.base import BaseTool, _get_input_type, _resolve_json_type, build_schema, safe_int
from ddev.ai.tools.types import ToolResult

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


class NoDocstringTool(BaseTool[SimpleInput]):
    @property
    def name(self) -> str:
        return "nodoc"

    async def __call__(self, tool_input: SimpleInput) -> ToolResult:
        return ToolResult(success=True)


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


class TestSafeInt:
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
    def test_valid_conversions(self, value, expected):
        assert safe_int(value, default=0) == expected

    @pytest.mark.parametrize("value", ["abc", "3.5", "", None, [], {}])
    def test_invalid_returns_default(self, value):
        assert safe_int(value, default=-1) == -1

    def test_default_none_returns_none_on_failure(self):
        assert safe_int("bad", default=None) is None

    def test_default_is_zero_when_omitted(self):
        assert safe_int("bad") == 0
        assert safe_int([1]) == 0


# ---------------------------------------------------------------------------
# _resolve_json_type
# ---------------------------------------------------------------------------


class TestResolveJsonType:
    @pytest.mark.parametrize(
        "hint,expected",
        [
            (str, "string"),
            (int, "integer"),
            (float, "number"),
            (bool, "boolean"),
        ],
    )
    def test_primitives(self, hint, expected):
        assert _resolve_json_type(hint) == expected

    def test_unknown_type_returns_none(self):
        assert _resolve_json_type(list) is None
        assert _resolve_json_type(dict) is None

    def test_optional_type_returns_type_of_non_none_member(self):
        assert _resolve_json_type(str | None) == "string"
        assert _resolve_json_type(int | None) == "integer"

    def test_multi_union_returns_none(self):
        # str | int has no single JSON type mapping
        assert _resolve_json_type(str | int) is None


# ---------------------------------------------------------------------------
# build_schema
# ---------------------------------------------------------------------------


class TestBuildSchema:
    def test_top_level_type_is_object(self):
        schema = build_schema(SimpleInput)
        assert schema["type"] == "object"

    def test_required_field_in_required_list(self):
        schema = build_schema(SimpleInput)
        assert schema["required"] == ["message"]

    def test_property_description_from_annotation(self):
        schema = build_schema(SimpleInput)
        assert schema["properties"]["message"]["description"] == "A message to echo"

    def test_property_type_from_annotation(self):
        schema = build_schema(SimpleInput)
        assert schema["properties"]["message"]["type"] == "string"

    def test_field_with_default_not_in_required(self):
        schema = build_schema(FullInput)
        assert "optional_int" not in schema.get("required", [])
        assert "flag" not in schema.get("required", [])

    def test_required_field_still_present_alongside_optionals(self):
        schema = build_schema(FullInput)
        assert "required_str" in schema["required"]

    def test_bool_field_resolves_to_boolean_type(self):
        schema = build_schema(FullInput)
        assert schema["properties"]["flag"]["type"] == "boolean"

    def test_no_required_key_when_all_fields_have_defaults(self):
        @dataclass
        class AllOptional:
            x: Annotated[str, "x"] = "default"
            y: Annotated[int, "y"] = 0

        schema = build_schema(AllOptional)
        assert "required" not in schema

    def test_properties_key_always_present(self):
        schema = build_schema(SimpleInput)
        assert "properties" in schema

    def test_unsupported_type_raises_type_error(self):
        @dataclass
        class BadInput:
            field: Annotated[str | int, "ambiguous"]

        with pytest.raises(TypeError, match="BadInput.field"):
            build_schema(BadInput)


# ---------------------------------------------------------------------------
# _get_input_type
# ---------------------------------------------------------------------------


class TestGetInputType:
    def test_returns_correct_input_type(self):
        assert _get_input_type(EchoTool) is SimpleInput
        assert _get_input_type(FullInputTool) is FullInput

    def test_unparameterized_subclass_raises_type_error(self):
        # A class that extends BaseTool without a type argument cannot be resolved
        class BareSubclass(BaseTool):  # type: ignore[type-arg]
            @property
            def name(self) -> str:
                return "bare"

            async def __call__(self, tool_input) -> ToolResult:  # type: ignore[override]
                return ToolResult(success=True)

        with pytest.raises(TypeError, match="BareSubclass"):
            _get_input_type(BareSubclass)

    def test_resolves_through_concrete_parent(self):
        class ChildTool(EchoTool):
            pass

        assert _get_input_type(ChildTool) is SimpleInput

    def test_resolves_through_intermediate_generic(self):
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


class TestBaseTool:
    def test_name_property(self):
        assert EchoTool().name == "echo"

    def test_description_comes_from_class_docstring(self):
        assert EchoTool().description == "Echo the message back."

    def test_description_is_empty_string_when_no_docstring(self):
        assert NoDocstringTool().description == ""

    def test_input_schema_matches_build_schema_for_input_type(self):
        assert EchoTool().input_schema == build_schema(SimpleInput)

    def test_definition_has_correct_name(self):
        assert EchoTool().definition["name"] == "echo"

    def test_definition_has_correct_description(self):
        assert EchoTool().definition["description"] == "Echo the message back."

    def test_definition_has_correct_input_schema(self):
        assert EchoTool().definition["input_schema"] == build_schema(SimpleInput)

    def test_cannot_instantiate_abstract_base_directly(self):
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore[abstract]

    # --- run(): happy path ---

    def test_run_valid_input_returns_success(self):
        result = asyncio.run(EchoTool().run({"message": "hello"}))
        assert result.success is True
        assert result.data == "hello"

    # --- run(): input validation failures ---

    def test_run_missing_required_field_returns_failure(self):
        result = asyncio.run(EchoTool().run({}))
        assert result.success is False
        assert result.error is not None

    def test_run_unexpected_extra_field_returns_failure(self):
        result = asyncio.run(EchoTool().run({"message": "hi", "extra": "oops"}))
        assert result.success is False

    # --- run(): __call__ exception handling ---

    def test_run_captures_exception_from_call(self):
        result = asyncio.run(FailingTool().run({"message": "boom"}))
        assert result.success is False
        assert "RuntimeError" in result.error
        assert "something went wrong" in result.error

    def test_run_never_propagates_exception_from_call(self):
        # run() must always return a ToolResult, never raise
        result = asyncio.run(FailingTool().run({"message": "boom"}))
        assert isinstance(result, ToolResult)
