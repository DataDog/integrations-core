from pathlib import Path

import pytest

from ddev.config.file import (
    ConfigFileWithOverrides,
    build_line_index_with_multiple_entries,
    deep_merge_with_list_handling,
)


def test_no_local_file(mocker, tmp_path: Path, config_file: ConfigFileWithOverrides):
    # Load the file
    config_file.load()
    assert config_file.combined_model.raw_data == config_file.global_model.raw_data


def test_with_local_file(mocker, config_file: ConfigFileWithOverrides, helpers):
    # Write a local toml to the local file. It includes a new repo and sets the value of repo to it.
    # This should be acceptable and pass validation
    with open(config_file.local_path, "w") as f:
        f.write(
            helpers.dedent(
                """
            repo = "local"

            [github]
            user = "test_user_12345"
            token = "test_token_12345"

            [repos]
            local = "local_repo"
            """
            )
        )

    # Load the file
    config_file.load()

    assert config_file.combined_model.github.user == "test_user_12345"
    assert config_file.combined_model.github.token == "test_token_12345"
    assert config_file.combined_model.repos['local'] == "local_repo"
    assert config_file.combined_model.repo.name == "local"
    assert config_file.combined_model.repo.path == "local_repo"
    # Still keeps other repos from global
    for repo in config_file.global_model.repos:
        assert config_file.combined_model.repos[repo] == config_file.global_model.repos[repo]
    # Verify other config values remain unchanged
    assert config_file.combined_model.agent.name == config_file.global_model.agent.name
    assert config_file.combined_model.org.name == config_file.global_model.org.name


@pytest.mark.parametrize(
    "dict_a, dict_b, expected",
    [
        # Basic merging
        (
            {"a": 1},
            {"b": 2},
            {"a": 1, "b": 2},
        ),
        # Overwriting values
        (
            {"a": 1, "b": 2},
            {"b": 3},
            {"a": 1, "b": 3},
        ),
        # List concatenation
        (
            {"a": [1, 2]},
            {"a": [3, 4]},
            {"a": [1, 2, 3, 4]},
        ),
        # Nested dictionary merging
        (
            {"a": {"b": 1, "c": 2}},
            {"a": {"c": 3, "d": 4}},
            {"a": {"b": 1, "c": 3, "d": 4}},
        ),
        # Complex nested structure with lists
        (
            {"a": {"b": [1, 2], "c": {"d": [3, 4]}}},
            {"a": {"b": [5], "c": {"d": [6]}}},
            {"a": {"b": [1, 2, 5], "c": {"d": [3, 4, 6]}}},
        ),
        # Empty dictionaries
        (
            {},
            {"a": 1},
            {"a": 1},
        ),
        (
            {"a": 1},
            {},
            {"a": 1},
        ),
        # Mixed types (non-matching types)
        (
            {"a": [1, 2]},
            {"a": {"b": 3}},  # List replaced by dict
            {"a": {"b": 3}},
        ),
        (
            {"a": {"b": 1}},
            {"a": [1, 2]},  # Dict replaced by list
            {"a": [1, 2]},
        ),
        # Deep nested structures with multiple types
        (
            {
                "a": {"b": [1, 2], "c": {"d": 3}},
                "e": [4, 5],
                "f": 6,
            },
            {
                "a": {"b": [7], "c": {"d": 8, "e": 9}},
                "e": [10],
                "g": 11,
            },
            {
                "a": {"b": [1, 2, 7], "c": {"d": 8, "e": 9}},
                "e": [4, 5, 10],
                "f": 6,
                "g": 11,
            },
        ),
        # Edge case: empty lists
        (
            {"a": []},
            {"a": [1, 2]},
            {"a": [1, 2]},
        ),
        # Edge case: nested empty structures
        (
            {"a": {"b": {}}},
            {"a": {"b": {"c": 1}}},
            {"a": {"b": {"c": 1}}},
        ),
        # Edge case: None values
        (
            {"a": None},
            {"a": 1},
            {"a": 1},
        ),
        # Edge case: same values
        (
            {"a": 1, "b": [1, 2]},
            {"a": 1, "b": [1, 2]},
            {"a": 1, "b": [1, 2, 1, 2]},
        ),
    ],
    ids=[
        "basic_merging",
        "overwriting_values",
        "list_concatenation",
        "nested_dict_merging",
        "complex_nested_with_lists",
        "empty_dict_a",
        "empty_dict_b",
        "list_to_dict",
        "dict_to_list",
        "deep_nested_multiple_types",
        "empty_list",
        "nested_empty_structures",
        "none_values",
        "same_values",
    ],
)
def test_deep_merge_with_list_handling(dict_a, dict_b, expected):
    """Test deep_merge_with_list_handling with various edge cases."""
    result = deep_merge_with_list_handling(dict_a, dict_b)
    assert result == expected


def test_deep_merge_with_list_handling_immutability():
    """Test that the original dictionaries are not modified during merge."""
    dict_a = {"a": {"b": [1, 2]}}
    dict_b = {"a": {"b": [3, 4]}}
    original_a = dict_a.copy()
    original_b = dict_b.copy()

    deep_merge_with_list_handling(dict_a, dict_b)

    assert dict_a == original_a, "Input dictionary a was modified"
    assert dict_b == original_b, "Input dictionary b was modified"


def test_deep_merge_with_list_handling_nested_immutability():
    """Test that nested structures in original dictionaries are not modified during merge."""
    dict_a = {"a": {"b": [1, 2]}}
    dict_b = {"a": {"b": [3, 4]}}
    original_a_nested = dict_a["a"]["b"].copy()
    original_b_nested = dict_b["a"]["b"].copy()

    deep_merge_with_list_handling(dict_a, dict_b)

    assert dict_a["a"]["b"] == original_a_nested, "Nested list in dictionary a was modified"
    assert dict_b["a"]["b"] == original_b_nested, "Nested list in dictionary b was modified"


def test_append_line_sources(helpers, config_file: ConfigFileWithOverrides):
    lines = ["repo = 'core'", "agent = 'dev'", "org = 'default'", "", "something: 'something'"]

    lines_sources = {
        0: "config.toml:1",
        1: "config.toml:2",
        2: "config.toml:3",
        4: "config.toml:5",
    }

    expected = helpers.dedent(
        """
        repo = 'core'           # config.toml:1
        agent = 'dev'           # config.toml:2
        org = 'default'         # config.toml:3

        something: 'something'  # config.toml:5"""
    )

    assert config_file._build_read_string(lines, lines_sources) == expected


def test_append_line_sources_with_scaped_characters(helpers, config_file: ConfigFileWithOverrides):
    lines = ["repo = 'core'", "agent = 'dev'", "org = 'default'", "", "something: 'something\\else'"]

    lines_sources = {
        0: "config.toml:1",
        1: "config.toml:2",
        2: "config.toml:3",
        4: "config.toml:5",
    }

    # Escaped characters count as 1, if the escaped character is in the longest line
    # this will affect the padding of the line. This test is kept mainly for documentation
    # as this is an edge case that is not expected to happen mostly with paths in Windows
    expected = helpers.dedent(
        """
        repo = 'core'                # config.toml:1
        agent = 'dev'                # config.toml:2
        org = 'default'              # config.toml:3

        something: 'something\\else'  # config.toml:5"""
    )

    assert config_file._build_read_string(lines, lines_sources) == expected


def test_build_line_index_with_single_entry():
    content = "line1\nline2\nline3"
    index = build_line_index_with_multiple_entries(content)

    assert index == {"line1": [1], "line2": [2], "line3": [3]}


def test_build_line_index_with_multiple_entries():
    content = "line1\nline1\nline2\nline1\nline3"
    index = build_line_index_with_multiple_entries(content)

    assert index == {"line1": [1, 2, 4], "line2": [3], "line3": [5]}


def test_build_line_index_with_empty_lines():
    content = "line1\n\nline2\n\nline3"
    index = build_line_index_with_multiple_entries(content)

    assert index == {"line1": [1], "": [2, 4], "line2": [3], "line3": [5]}
