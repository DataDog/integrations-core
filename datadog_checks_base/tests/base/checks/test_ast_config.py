# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math

import pytest

from datadog_checks.base.checks import _config_ast


@pytest.mark.parametrize(
    'input_str, expected_value',
    [
        pytest.param("inf", float("inf"), id="positive_inf"),
        pytest.param("-inf", float("-inf"), id="negative_inf"),
        pytest.param("1", 1, id="integer"),
        pytest.param("hello inf", "hello inf", id="string_with_inf"),
    ],
)
def test_ast_config_parse_values(input_str, expected_value):
    assert _config_ast.parse(input_str) == expected_value


def test_ast_config_parse_nan():
    assert _config_ast.parse("nan") != _config_ast.parse("nan")
    assert math.isnan(_config_ast.parse("nan"))


def test_ast_config_parse_dict_with_specials():
    result = _config_ast.parse("{'a': inf, 'b': -inf, 'c': nan}")
    assert result['a'] == float('inf')
    assert result['b'] == float('-inf')
    assert math.isnan(result['c'])


def test_ast_config_parse_invalid():
    # Should return the original string if parsing fails
    s = "not a python literal"
    assert _config_ast.parse(s) == s
