# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.git import (
    ChangedFile,
    ChangeType,
    CIContext,
    get_changed_files,
    is_git_warning_line,
    parse_name_status,
)


class RecordingGit:
    """A fake git provider that records invocations and returns canned output."""

    def __init__(self, output: str = "") -> None:
        self.output = output
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        return self.output


@pytest.mark.parametrize(
    "line, expected",
    [
        pytest.param("warning: LF will be replaced by CRLF in foo.txt", True, id="crlf-warning"),
        pytest.param("The file will have its original line endings in your working directory", True, id="endings"),
        pytest.param("A\tfoo/bar.py", False, id="added-record"),
        pytest.param("", False, id="blank"),
    ],
)
def test_is_git_warning_line(line, expected):
    assert is_git_warning_line(line) is expected


def test_parse_name_status_single_path_statuses():
    # Added, modified, deleted, and a type change (T) which is treated as a modification.
    output = "A\tfoo/added.py\nM\tfoo/modified.py\nD\tfoo/deleted.py\nT\tfoo/typed.py\n"

    assert parse_name_status(output) == [
        ChangedFile(change_type=ChangeType.ADDED, path="foo/added.py"),
        ChangedFile(change_type=ChangeType.MODIFIED, path="foo/modified.py"),
        ChangedFile(change_type=ChangeType.DELETED, path="foo/deleted.py"),
        ChangedFile(change_type=ChangeType.MODIFIED, path="foo/typed.py"),
    ]


def test_parse_name_status_renamed_and_copied_use_destination():
    output = "R100\tfoo/old.py\tfoo/new.py\nC075\tbar/src.py\tbar/copy.py\n"

    assert parse_name_status(output) == [
        ChangedFile(change_type=ChangeType.RENAMED, path="foo/new.py", previous_path="foo/old.py"),
        ChangedFile(change_type=ChangeType.COPIED, path="bar/copy.py", previous_path="bar/src.py"),
    ]


def test_parse_name_status_skips_warnings_and_blank_lines():
    output = (
        "warning: LF will be replaced by CRLF in foo/bar.py\n"
        "A\tfoo/bar.py\n"
        "\n"
        "The file will have its original line endings in your working directory\n"
        "M\tfoo/baz.py\n"
    )

    assert parse_name_status(output) == [
        ChangedFile(change_type=ChangeType.ADDED, path="foo/bar.py"),
        ChangedFile(change_type=ChangeType.MODIFIED, path="foo/baz.py"),
    ]


def test_parse_name_status_deduplicates_preserving_order():
    output = "M\tb.py\nA\ta.py\nM\tb.py\n"

    assert parse_name_status(output) == [
        ChangedFile(change_type=ChangeType.MODIFIED, path="b.py"),
        ChangedFile(change_type=ChangeType.ADDED, path="a.py"),
    ]


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("A", id="single-path-no-tab"),
        pytest.param("R100\tonly-source", id="rename-missing-destination"),
    ],
)
def test_parse_name_status_raises_on_malformed_line(line):
    # A malformed record must fail loudly rather than silently dropping a changed path.
    with pytest.raises(ValueError):
        parse_name_status(f"{line}\n")


@pytest.mark.parametrize(
    "context, target_branch, expected_call",
    [
        pytest.param(
            CIContext.PULL_REQUEST,
            "origin/master",
            ("diff", "--name-status", "origin/master...abc123"),
            id="pull-request-merge-base",
        ),
        pytest.param(
            CIContext.DEFAULT_BRANCH,
            None,
            ("diff", "--name-status", "abc123^1", "abc123"),
            id="default-branch-first-parent",
        ),
    ],
)
def test_get_changed_files_uses_the_right_comparison(context, target_branch, expected_call):
    git = RecordingGit("M\tfoo/bar.py\n")

    changed = get_changed_files("abc123", context=context, target_branch=target_branch, git=git)

    assert git.calls == [expected_call]
    assert changed == [ChangedFile(change_type=ChangeType.MODIFIED, path="foo/bar.py")]


def test_get_changed_files_pull_request_requires_target_branch():
    with pytest.raises(ValueError):
        get_changed_files("abc123", context=CIContext.PULL_REQUEST, target_branch=None, git=RecordingGit())
