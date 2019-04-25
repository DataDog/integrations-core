import os

from datadog_checks.dev.config_validator.config_block import ParamProperties, ConfigBlock, _get_end_of_param_declaration_block, _parse_description, _is_object, _should_recurse, _is_comment, _parse_comment


def test_param_properties():
    def function_wrapper(string):
        mocked_config_lines = [string]
        return ParamProperties.parse_from_string(0, mocked_config_lines, 0)

    test_cases = [
        ("## @param var - string - required", "var", "string", True, None),
        ("## @param varname_with_underscores - custom object type with spaces - optional", "varname_with_underscores", "custom object type with spaces", False, None),
        ("## @param var - int - optional - default: 3306", "var", "int", False, "3306")
    ]

    for c in test_cases:
        param_prop = function_wrapper(c[0])
        assert param_prop.var_name == c[1]
        assert param_prop.type_name == c[2]
        assert param_prop.required == c[3]
        assert param_prop.default_value == c[4]


def test_config_block():
    test_case_1 = [
        "## @param var - string - required",
        "## Documentation line 1",
        "## Documentation line 2",
        "#"
        "param: value"
    ]
    test_case_2 = [
        "  ## @param var - string - required",
        "  ## Documentation line 1",
        "  ## Documentation line 2",
        "  #"
        "  param: value"
    ]

    cfg_block_1 = ConfigBlock.parse_from_strings(0, test_case_1, 0)
    cfg_block_2 = ConfigBlock.parse_from_strings(0, test_case_2, 2)

    assert cfg_block_1.param_prop.var_name == "var"
    assert cfg_block_2.param_prop.var_name == "var"
    assert cfg_block_1.param_prop.type_name == "string"
    assert cfg_block_2.param_prop.type_name == "string"
    assert cfg_block_1.param_prop.required
    assert cfg_block_2.param_prop.required
    assert cfg_block_1.param_prop.default_value is None
    assert cfg_block_2.param_prop.default_value is None


def test_get_end_of_param_declaration_block():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_1.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    test_cases = [
        # start_line, end_line, indent, expected result
        (0, 27, 0, 5),
        (5, 27, 0, 13),
        (13, 27, 0, 17),
        (19, 27, 2, None),
        (20, 27, 4, 25)

    ]

    for c in test_cases:
        end = _get_end_of_param_declaration_block(c[0], c[1], config_lines, c[2])
        assert end == c[3]


def test_parse_description():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_2.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    expected = " Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n Suspendisse erat enim, tincidunt ac libero sit amet"

    test_cases = [
        # start, end, indent, expected_description, expected_new_idx
        (0, 10, 0, expected, 3),
        (4, 10, 0, None, None),
        (7, 10, 2, expected, 10)
    ]

    for c in test_cases:
        description, idx = _parse_description(c[0], c[1], config_lines, c[2])
        assert description == c[3]
        assert idx == c[4]


def test_is_object():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_3.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    obj_param_prop = ParamProperties(None, "object", None, None)
    non_obj_param_prop = ParamProperties(None, "x", None, None)

    test_cases = [
        # idx, indent, param_prop, expected
        (0, 0, obj_param_prop, None),
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

    for c in test_cases:
        is_object = _is_object(c[0], config_lines, c[1], c[2])
        assert is_object == c[3]


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
        (29, 0, True, None)
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
        (12, 2, True)
    ]

    for c in test_cases:
        status = _is_comment(c[0], config_lines, c[1])
        assert status == c[2]


def test_parse_comment():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_config_block_5.yaml'), 'r')
    config_lines = test_file.read().split('\n')
    test_file.close()

    #def _parse_comment(start, config_lines):

    test_cases = [
        # idx, expected
        (6, " Multi-line comment\n starting here\n key: value\n - 1\n - 2", 12),
        (12, " Comment with\n a mistake in indentation\n must still be read as a comment", 16)
    ]

    for c in test_cases:
        comment, next_idx = _parse_comment(c[0], config_lines)
        assert comment == c[1]
        assert next_idx == c[2]



