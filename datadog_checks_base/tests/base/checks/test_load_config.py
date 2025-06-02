# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math
from contextlib import nullcontext

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks import _config_ast


class TestLoadConfig:
    @pytest.mark.parametrize(
        "config_input,expectation",
        [
            pytest.param('raw_foo: bar', nullcontext({'raw_foo': 'bar'}), id="valid_yaml"),
            pytest.param('invalid:mapping', nullcontext('invalid:mapping'), id="invalid_yaml_returned_as_string"),
            pytest.param('', nullcontext(None), id="empty_string_returns_none"),
            pytest.param(':', pytest.raises(ValueError, match='Failed to load config: '), id="invalid_yaml_raises_error"),
        ],
    )
    def test_load_config(self, config_input, expectation):
        with expectation as expected_result:
            result = AgentCheck.load_config(config_input)
            assert result == expected_result

    @pytest.mark.parametrize(
        'yaml_str, expected_object',
        [
            pytest.param("boolean: true", {"boolean": True}, id="boolean_true"),
            pytest.param("boolean: false", {"boolean": False}, id="boolean_false"),
            pytest.param("number: .inf", {"number": float("inf")}, id="number_inf"),
            pytest.param("number: .INF", {"number": float("inf")}, id="number_capital_inf"),
            pytest.param("number: -.inf", {"number": float("-inf")}, id="number_neg_inf"),
            pytest.param("number: +.inf", {"number": float("inf")}, id="number_plus_inf"),
            pytest.param("number: -.INF", {"number": float("-inf")}, id="number_capital_neg_inf"),
            pytest.param("number: 0xF", {"number": 15.0}, id="number_hex"),
            pytest.param("number: 0b1111", {"number": 15.0}, id="number_binary"),
            pytest.param('string: "hi inf"', {"string": "hi inf"}, id="string_inf_quoted"),
            pytest.param("string: hi inf", {"string": "hi inf"}, id="string_inf_not_quoted"),
            pytest.param(
                'string: "this inf is in the middle"',
                {"string": "this inf is in the middle"},
                id="string_inf_in_the_middle_quoted",
            ),
            pytest.param(
                "string: this inf is in the middle",
                {"string": "this inf is in the middle"},
                id="string_inf_in_the_middle_not_quoted",
            ),
            pytest.param("string: infinity", {"string": "infinity"}, id="string_infinity"),
        ],
    )
    def test_load_config_values(self, yaml_str, expected_object):
        assert AgentCheck.load_config(yaml_str) == expected_object

    @pytest.mark.parametrize(
        'yaml_str, expected_key, expected_value, expected_type',
        [
            pytest.param("number: !!int 1 ", "number", 1, int, id="number_int"),
            pytest.param("number: !!float 1 ", "number", 1.0, float, id="number_float"),
            pytest.param("string: !!str inf", "string", "inf", str, id="string_str_inf"),
            pytest.param("string: inf", "string", "inf", str, id="string_inf"),
            pytest.param('string: ".inf"', "string", ".inf", str, id="string_inf_quoted"),
        ],
    )
    def test_load_config_explicit_types(self, yaml_str, expected_key, expected_value, expected_type):
        config = AgentCheck.load_config(yaml_str)
        assert config == {expected_key: expected_value}
        assert isinstance(config[expected_key], expected_type)

    def test_load_config_nan(self):
        config = AgentCheck.load_config("number: .nan")
        assert "number" in config
        assert math.isnan(config["number"])


class TestAstConfig:
    @pytest.mark.parametrize(
        'input_str, expected_value',
        [
            pytest.param("inf", float("inf"), id="positive_inf"),
            pytest.param("-inf", float("-inf"), id="negative_inf"),
            pytest.param("1", 1, id="integer"),
            pytest.param("hello inf", "hello inf", id="string_with_inf"),
        ],
    )
    def test_ast_config_parse_values(self, input_str, expected_value):
        assert _config_ast.parse(input_str) == expected_value

    def test_ast_config_parse_nan(self):
        assert _config_ast.parse("nan") != _config_ast.parse("nan")
        assert math.isnan(_config_ast.parse("nan"))

    def test_ast_config_parse_dict_with_specials(self):
        result = _config_ast.parse("{'a': inf, 'b': -inf, 'c': nan}")
        assert result['a'] == float('inf')
        assert result['b'] == float('-inf')
        assert math.isnan(result['c'])

    def test_ast_config_parse_invalid(self):
        # Should return the original string if parsing fails
        s = "not a python literal"
        assert _config_ast.parse(s) == s
