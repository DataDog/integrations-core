# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math
from contextlib import nullcontext

import pytest

from datadog_checks.base import AgentCheck


@pytest.mark.parametrize(
    "config_input,expectation",
    [
        pytest.param('raw_foo: bar', nullcontext({'raw_foo': 'bar'}), id="valid_yaml"),
        pytest.param('invalid:mapping', nullcontext('invalid:mapping'), id="invalid_yaml_returned_as_string"),
        pytest.param('', nullcontext(None), id="empty_string_returns_none"),
        pytest.param(':', pytest.raises(ValueError, match='Failed to load config: '), id="invalid_yaml_raises_error"),
    ],
)
def test_load_config(config_input, expectation):
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
def test_load_config_values(yaml_str, expected_object):
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
def test_load_config_explicit_types(yaml_str, expected_key, expected_value, expected_type):
    config = AgentCheck.load_config(yaml_str)
    assert config == {expected_key: expected_value}
    assert isinstance(config[expected_key], expected_type)


def test_load_config_nan():
    config = AgentCheck.load_config("number: .nan")
    assert "number" in config
    assert math.isnan(config["number"])


@pytest.mark.parametrize(
    'yaml_str, expected_object',
    [
        pytest.param(
            "tag: テスト",
            {"tag": "テスト"},
            id="japanese_characters",
        ),
        pytest.param(
            "chinese: 中文测试",
            {"chinese": "中文测试"},
            id="chinese_characters",
        ),
        pytest.param(
            "korean: 한국어",
            {"korean": "한국어"},
            id="korean_characters",
        ),
    ],
)
def test_load_config_unicode(yaml_str, expected_object):
    """Test that load_config properly handles Unicode characters including Japanese, Chinese, Korean, and emoji.
    This is especially important on Windows where the system locale may not default to UTF-8."""
    config = AgentCheck.load_config(yaml_str)
    assert config == expected_object
