# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks import _config_ast


class TestLoadConfig:
    def test_load_config(self):
        assert AgentCheck.load_config('raw_foo: bar') == {'raw_foo': 'bar'}
        assert AgentCheck.load_config('invalid:mapping') == 'invalid:mapping'
        assert AgentCheck.load_config('') is None

        with pytest.raises(ValueError, match='Failed to load config: '):
            AgentCheck.load_config(':')

    @pytest.mark.parametrize(
        'yaml_str, expected_object',
        [
            ("boolean: true", {"boolean": True}),
            ("boolean: false", {"boolean": False}),
            ("number: .inf", {"number": float("inf")}),
            ("number: .INF", {"number": float("inf")}),
            ("number: -.inf", {"number": float("-inf")}),
            ("number: +.inf", {"number": float("inf")}),
            ("number: -.INF", {"number": float("-inf")}),
            ("number: 0xF", {"number": 15.0}),  # Hexadecimal
            ("number: 0b1111", {"number": 15.0}),  # Binary
            ('string: "hi inf"', {"string": "hi inf"}),
            ("string: hi inf", {"string": "hi inf"}),
            ('string: "this inf is in the middle"', {"string": "this inf is in the middle"}),
            ("string: this inf is in the middle", {"string": "this inf is in the middle"}),
            ("string: infinity", {"string": "infinity"}),
        ],
    )
    def test_load_config_values(self, yaml_str, expected_object):
        assert AgentCheck.load_config(yaml_str) == expected_object

    @pytest.mark.parametrize(
        'yaml_str, expected_key, expected_value, expected_type',
        [
            ("number: !!int 1 ", "number", 1, int),
            ("number: !!float 1 ", "number", 1.0, float),
            ("string: !!str inf", "string", "inf", str),
            ("string: inf", "string", "inf", str),
            ('string: ".inf"', "string", ".inf", str),
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
    def test_ast_config_parse_inf(self):
        assert _config_ast.parse("inf") == float("inf")
        assert _config_ast.parse("-inf") == float("-inf")
        assert _config_ast.parse("nan") != _config_ast.parse("nan")

    def test_parse_values_without_special_keywords(self):
        assert _config_ast.parse("1") == 1
        assert _config_ast.parse("hello inf") == "hello inf"

    def test_ast_config_parse_dict_with_specials(self):
        result = _config_ast.parse("{'a': inf, 'b': -inf, 'c': nan}")
        assert result['a'] == float('inf')
        assert result['b'] == float('-inf')
        assert math.isnan(result['c'])

    def test_ast_config_parse_invalid(self):
        # Should return the original string if parsing fails
        s = "not a python literal"
        assert _config_ast.parse(s) == s
