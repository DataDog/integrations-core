# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.tooling.config_validator.config_block import MAX_COMMENT_LENGTH, ConfigBlock, ParamProperties
from datadog_checks.dev.tooling.config_validator.validator import _check_no_duplicate_names


def create(name, type_name="string", description="Non-empty description"):
    param_prop = ParamProperties(name, type_name, False)
    return ConfigBlock(param_prop, description, 0, 0)


def test_check_no_duplicate_names():
    blocks_no_duplicate = [
        [
            create("1"),
            create("2"),
            [create("1"), create("2"), [create("1"), create("2")], [create("1"), create("2")]],
            create("3"),
        ],
        create("1"),
    ]
    errors = []
    _check_no_duplicate_names(blocks_no_duplicate, errors)
    assert len(errors) == 0


def test_check_duplicate_names():
    blocks_two_duplicates = [
        [
            create("1"),  # Duplicate #1
            create("2"),
            [
                create("1"),
                create("2"),  # Duplicate #2
                [create("1"), create("2")],
                [create("1"), create("2")],
                create("2"),  # Duplicate #2
            ],
            create("3"),
            create("1"),  # Duplicate #1
        ],
        create("1"),
    ]
    errors = []
    _check_no_duplicate_names(blocks_two_duplicates, errors)
    assert len(errors) == 2
    assert errors[0].error_str == "Duplicate variable with name 1"
    assert errors[1].error_str == "Duplicate variable with name 2"


def test_config_block_validate_description():
    test_cases = [
        (create("name", description=" Line 1\n Line 2\n Line 3"), True),
        (create("name", description=" \n    \n     \n\n"), False, "Empty description"),
        (create("name", description='A' * (MAX_COMMENT_LENGTH + 1)), False, "Description too long"),
    ]

    for c in test_cases:
        errors = []
        c[0]._validate_description(errors)
        if c[1]:
            assert len(errors) == 0
        else:
            assert len(errors) == 1
            assert c[2] in str(errors[0])


def test_validate_type():
    test_cases = [
        (create("name", "boolean"), True),
        (create("name", "string"), True),
        (create("name", "integer"), True),
        (create("name", "double"), True),
        (create("name", "float"), True),
        (create("name", "object"), True),
        (create("name", "list of anything_really"), True),
        (create("name", "list of something"), True),
        (create("name", "dictionary"), True),
        (create("name", "custom object"), False),
    ]

    for c in test_cases:
        errors = []
        c[0]._validate_type(errors)
        if c[1]:
            assert len(errors) == 0
        else:
            type_name = c[0].param_prop.type_name
            assert len(errors) == 1
            assert errors[0].error_str == "Type {} is not accepted".format(type_name)
