# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.tooling.config_validator.utils import (
    get_end_of_part,
    get_indent,
    is_at_least_indented,
    is_blank,
    is_exactly_indented,
)


def test_is_blank():
    blank_lines = ["", " ", "       ", "   - "]
    non_blank_lines = ["simple_text", "#simple_text", "# ", "   - {}", "  - hey"]
    for l in blank_lines:
        assert is_blank(l)

    for l in non_blank_lines:
        assert not is_blank(l)


def test_is_at_least_indented():
    test_correct_cases = [
        # (indentation, string)
        (0, "key: value"),
        (0, "# Simple comment"),
        (0, "           key:value"),
        (1, " key: value"),
        (1, " # Simple comment"),
        (1, "- k"),
        (2, "- k"),
        (2, "  key: value"),
        (2, "  # Simple comment"),
        (2, "- list_item_1"),
        (4, "  - list item 2"),
    ]

    test_wrong_cases = [
        # (indentation, string)
        (1, "# Simple comment"),
        (1, " "),
        (2, "  "),
        (2, "   "),
        (0, "  "),
        (5, "- k"),
    ]

    for c in test_correct_cases:
        assert is_at_least_indented(c[1], c[0])

    for c in test_wrong_cases:
        assert not is_at_least_indented(c[1], c[0])


def test_is_exactly_indented():
    test_correct_cases = [
        # (indentation, string)
        (0, "key: value"),
        (0, "# Simple comment"),
        (1, " key: value"),
        (1, " # Simple comment"),
        (2, "- k"),
        (2, "  key: value"),
        (2, "  # Simple comment"),
        (2, "- list_item_1"),
        (4, "  - list item 2"),
    ]

    test_wrong_cases = [
        # (indentation, string)
        (0, "           key:value"),  # This one has was considered as correct for the previous test
        (1, "- k"),
        (1, "# Simple comment"),
        (1, " "),
        (2, "  "),
        (2, "   "),
        (0, "  "),
        (5, "- k"),
    ]

    for c in test_correct_cases:
        assert is_exactly_indented(c[1], c[0])

    for c in test_wrong_cases:
        assert not is_exactly_indented(c[1], c[0])


def test_get_indent():
    test_cases = [(0, "key: value"), (1, " key: value"), (2, "  key: value"), (2, "- item"), (6, "  -   item")]

    for c in test_cases:
        assert get_indent(c[1]) == c[0]


def test_get_end_of_part():
    dir = os.path.dirname(__file__)
    test_file = open(os.path.join(dir, 'test_utils.yaml'), 'r')
    test_data = test_file.read().split('\n')
    test_file.close()

    test_cases = [
        # (lines of the yaml file, expected result)
        (list(range(0, 5)), None),
        (5, 10),
        (list(range(6, 10)), None),
        (10, 35),
        (11, 15),
        (list(range(12, 18)), None),
        (18, 35),
        (list(range(19, 22)), None),
        (23, 27),
        (list(range(24, 31)), None),
        (31, 35),
        (list(range(32, 36)), None),
    ]

    test_cases_with_optional_indent = [
        # (lines of the yaml file, optional indent parameter, expected result, )
        (13, 0, 35),
        (13, 2, 15),
        (19, 2, 35),
        (19, 6, None),
        (24, 6, 27),
    ]

    for c in test_cases:
        if isinstance(c[0], list):
            for el in c[0]:
                assert get_end_of_part(test_data, el) == c[1]
        else:
            assert get_end_of_part(test_data, c[0]) == c[1]

    for c in test_cases_with_optional_indent:
        assert get_end_of_part(test_data, c[0], indent=c[1]) == c[2]
