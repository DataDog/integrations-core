# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.tooling.config_validator.config_block import (
    ConfigBlock,
    ParamProperties,
    _get_end_of_param_declaration_block,
    _is_comment,
    _is_object,
    _parse_comment,
    _parse_description,
    _should_recurse,
)


def test_param_properties():
    def function_wrapper(string, errs):
        mocked_config_lines = [string]
        return ParamProperties.parse_from_string(0, mocked_config_lines, 0, errs)

    correct_test_cases = [
        ("## @param var - string - required", "var", "string", True, None, []),
        (
            "## @param varname_with_underscores - custom object type with spaces - optional",
            "varname_with_underscores",
            "custom object type with spaces",
            False,
            None,
            [],
        ),
        ("## @param var - int - optional - default: 3306", "var", "int", False, "3306", []),
    ]

    wrong_test_cases = [
        ("  ## @param var - string - required", "Content is not correctly indented"),
        ("## param var - string - required", "Expecting @param declaration"),
        ("## @param var - string - optionla", "Invalid @param declaration"),
        ("## @param var - string - optional - default:false", "Invalid @param declaration"),
    ]

    for c in correct_test_cases:
        param_prop = function_wrapper(c[0], [])
        assert param_prop.var_name == c[1]
        assert param_prop.type_name == c[2]
        assert param_prop.required == c[3]
        assert param_prop.default_value == c[4]

    for c in wrong_test_cases:
        errors = []
        param_prop = function_wrapper(c[0], errors)
        assert param_prop is None
        assert len(errors) == 1
        assert errors[0].error_str == c[1]


def test_config_block():
    test_case_1 = [
        "## @param var - string - required",
        "## Documentation line 1",
        "## Documentation line 2",
        "#",
        "param: value",
    ]
    test_case_2 = [
        "  ## @param var - string - required",
        "  ## Documentation line 1",
        "  ## Documentation line 2",
        "  #",
        "  param: value",
    ]

    cfg_block_1 = ConfigBlock.parse_from_strings(0, test_case_1, 0, [])
    cfg_block_2 = ConfigBlock.parse_from_strings(0, test_case_2, 2, [])

    for c in [cfg_block_1, cfg_block_2]:
        assert c.param_prop.var_name == "var"
        assert c.param_prop.type_name == "string"
        assert c.param_prop.required
        assert c.param_prop.default_value is None
        assert c.description == " Documentation line 1\n Documentation line 2"
        assert c.length == 5


def test_get_end_of_param_declaration_block():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_1.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()
    eof = len(config_lines)

    correct_test_cases = [
        # start_line, end_line, indent, expected result
        (0, 0, 5),
        (5, 0, 13),
        (13, 0, 17),
        (20, 4, 25),
    ]

    wrong_test_cases = [
        (19, 0, "Unexpected indentation, expecting 0 not 2"),
        (19, 2, "Expecting @param declaration"),
        (35, 0, "Blank line when reading description"),
        (40, 0, "Unexpected indentation, expecting 0 not 1"),
        (45, 0, "Cannot find end of block starting at line 45"),
    ]
    for c in correct_test_cases:
        end = _get_end_of_param_declaration_block(c[0], eof, config_lines, c[1], [])
        assert end == c[2]

    for c in wrong_test_cases:
        errors = []
        end = _get_end_of_param_declaration_block(c[0], eof, config_lines, c[1], errors)
        assert end is None
        assert len(errors) == 1
        assert errors[0].error_str == c[2]


def test_parse_description():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_2.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()
    eof = len(config_lines)
    expected = (
        " Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n"
        " Suspendisse erat enim, tincidunt ac libero sit amet"
    )

    correct_test_cases = [
        # start, end, indent, expected_description, expected_new_idx
        (0, 0, expected, 3),
        (7, 2, expected, 10),
    ]

    wrong_test_cases = [
        (7, 0, "Description is not correctly indented"),
        (4, 0, "Reached end of description without marker"),
        (11, 0, "Reached EOF while reading description"),
    ]

    for c in correct_test_cases:
        description, idx = _parse_description(c[0], eof, config_lines, c[1], [])
        assert description == c[2]
        assert idx == c[3]

    for c in wrong_test_cases:
        errors = []
        description, idx = _parse_description(c[0], eof, config_lines, c[1], errors)
        assert idx is None
        assert len(errors) == 1
        assert errors[0].error_str == c[2]


def test_is_object():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_3.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    obj_param_prop = ParamProperties("var", "object", None, None)
    non_obj_param_prop = ParamProperties("var", "x", None, None)

    test_cases = [
        # idx, indent, param_prop, expected
        (0, 0, obj_param_prop, False),
        (0, 0, non_obj_param_prop, False),
        (2, 0, obj_param_prop, True),
        (2, 0, non_obj_param_prop, False),
        (7, 0, obj_param_prop, True),
        (7, 0, non_obj_param_prop, False),
        (8, 2, obj_param_prop, True),
        (8, 2, non_obj_param_prop, False),
        (16, 0, obj_param_prop, True),
        (16, 0, non_obj_param_prop, False),
    ]

    test_cases_with_errors = [
        (0, 2, obj_param_prop, "Content is not correctly indented"),
        (0, 0, obj_param_prop, "Parameter var is declared as object but isn't one"),
    ]

    for c in test_cases:
        is_object = _is_object(c[0], config_lines, c[1], c[2], [])
        assert is_object == c[3]

    for c in test_cases_with_errors:
        errors = []
        is_object = _is_object(c[0], config_lines, c[1], c[2], errors)
        assert not is_object
        assert len(errors) == 1
        assert errors[0].error_str == c[3]


def test_should_recurse():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_4.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    test_cases = [
        # idx, indent, expected
        (0, 0, False, 4),
        (7, 0, True, None),
        (21, 0, False, 25),
        (29, 0, True, None),
    ]

    for c in test_cases:
        should_recurse, idx = _should_recurse(c[0], config_lines, c[1])
        assert should_recurse == c[2]
        assert idx == c[3]


def test_is_comment():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_5.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    test_cases = [
        # idx, indent, expected
        (0, 0, False),
        (0, 2, False),
        (6, 0, True),
        (6, 2, True),
        (12, 0, True),
        (12, 2, True),
    ]

    test_cases_with_errors = [(12, 0, True, "Comment block incorrectly indented")]

    for c in test_cases:
        status = _is_comment(c[0], config_lines, c[1], [])
        assert status == c[2]

    for c in test_cases_with_errors:
        errors = []
        status = _is_comment(c[0], config_lines, c[1], errors)
        assert status == c[2]
        assert len(errors) == 1
        assert errors[0].error_str == c[3]


def test_parse_comment():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_5.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    test_cases = [
        # idx, expected
        (6, " Multi-line comment\n starting here\n key: value\n - 1\n - 2", 12),
        (12, " Comment with\n a mistake in indentation\n must still be read as a comment", 16),
    ]

    for c in test_cases:
        comment, next_idx = _parse_comment(c[0], config_lines)
        assert comment == c[1]
        assert next_idx == c[2]
