from datadog_checks.dev.config_validator.validator import _check_no_duplicate_names
from datadog_checks.dev.config_validator.config_block import ConfigBlock, ParamProperties, MAX_COMMENT_LENGTH


def create(name, type_name="string", description="Non-empty description"):
    param_prop = ParamProperties(name, type_name, False)
    return ConfigBlock(param_prop, description, 0, 0)


def test_check_no_duplicate_names():
    blocks_no_duplicate = [
        [
            create("1"),
            create("2"),
            [
                create("1"),
                create("2"),
                [
                    create("1"),
                    create("2")
                ],
                [
                    create("1"),
                    create("2")
                ]
            ],
            create("3")
        ],
        create("1")
    ]
    assert len(_check_no_duplicate_names(blocks_no_duplicate)) == 0


def test_check_duplicate_names():
    blocks_two_duplicates = [
        [
            create("1"),  # Duplicate #1
            create("2"),
            [
                create("1"),
                create("2"),  # Duplicate #2
                [
                    create("1"),
                    create("2")
                ],
                [
                    create("1"),
                    create("2")
                ],
                create("2")  # Duplicate #2
            ],
            create("3"),
            create("1")  # Duplicate #1
        ],
        create("1")
    ]
    assert len(_check_no_duplicate_names(blocks_two_duplicates)) == 2


def tests_config_block_validate_description():
    test_cases = [
        (create("name", description=" Line 1\n Line 2\n Line 3"), True),
        (create("name", description=" \n    \n     \n\n"), False, "Empty description"),
        (create("name", description='A' * (MAX_COMMENT_LENGTH + 1)), False, "Description too long"),
    ]

    for c in test_cases:
        errs = c[0]._validate_description()
        if c[1]:
            assert len(errs) == 0
        else:
            assert len(errs) == 1
            assert c[2] in str(errs[0])


