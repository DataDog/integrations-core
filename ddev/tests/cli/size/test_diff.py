# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.size.diff import validate_parameters


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


@pytest.fixture
def mock_size_diff_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")
    mock_git_repo.__enter__.return_value = mock_git_repo
    mock_git_repo.__exit__.return_value = None

    def get_compressed_files_side_effect(*args, **kwargs):
        get_compressed_files_side_effect.counter += 1
        py_version = args[2]
        platform = args[3]
        if get_compressed_files_side_effect.counter % 2 == 1:
            return [
                {
                    "Name": "path1.py",
                    "Version": "1.1.1",
                    "Size_Bytes": 1000,
                    "Type": "Integration",
                    "Platform": platform,
                    "Python_Version": py_version,
                }
            ]  # before
        else:
            return [
                {
                    "Name": "path1.py",
                    "Version": "1.1.2",
                    "Size_Bytes": 1200,
                    "Type": "Integration",
                    "Platform": platform,
                    "Python_Version": py_version,
                },
                {
                    "Name": "path2.py",
                    "Version": "1.1.1",
                    "Size_Bytes": 500,
                    "Type": "Integration",
                    "Platform": platform,
                    "Python_Version": py_version,
                },
            ]  # after

    get_compressed_files_side_effect.counter = 0

    def get_compressed_dependencies_side_effect(*args, **kwargs):
        get_compressed_dependencies_side_effect.counter += 1
        platform = args[1]
        py_version = args[2]
        if get_compressed_dependencies_side_effect.counter % 2 == 1:
            return [
                {
                    "Name": "dep1",
                    "Version": "1.0.0",
                    "Size_Bytes": 2000,
                    "Type": "Dependency",
                    "Platform": platform,
                    "Python_Version": py_version,
                }
            ]  # before
        else:
            return [
                {
                    "Name": "dep1",
                    "Version": "1.1.0",
                    "Size_Bytes": 2500,
                    "Type": "Dependency",
                    "Platform": platform,
                    "Python_Version": py_version,
                },
                {
                    "Name": "dep2",
                    "Version": "1.0.0",
                    "Size_Bytes": 1000,
                    "Type": "Dependency",
                    "Platform": platform,
                    "Python_Version": py_version,
                },
            ]  # after

    get_compressed_dependencies_side_effect.counter = 0

    with (
        patch(
            "ddev.cli.size.utils.common_funcs.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch(
            "ddev.cli.size.utils.common_funcs.get_valid_versions",
            return_value=({"3.12"}),
        ),
        patch("ddev.cli.size.utils.common_funcs.GitRepo", return_value=mock_git_repo),
        patch("ddev.cli.size.utils.common_funcs.tempfile.mkdtemp", return_value="fake_repo"),
        patch("ddev.cli.size.utils.common_funcs.get_files", side_effect=get_compressed_files_side_effect),
        patch("ddev.cli.size.utils.common_funcs.get_dependencies", side_effect=get_compressed_dependencies_side_effect),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield


@pytest.fixture
def mock_size_diff_no_diff_dependencies():
    fake_repo = MagicMock()
    fake_repo.repo_dir = "fake_repo"
    fake_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")
    fake_repo.__enter__.return_value = fake_repo
    fake_repo.__exit__.return_value = None

    def get_files_side_effect(*args, **kwargs):
        py_version = args[2]
        platform = args[3]
        return [
            {
                "Name": "path1.py",
                "Version": "1.0.0",
                "Size_Bytes": 1000,
                "Type": "Integration",
                "Platform": platform,
                "Python_Version": py_version,
            },
            {
                "Name": "path2.py",
                "Version": "1.0.0",
                "Size_Bytes": 500,
                "Type": "Integration",
                "Platform": platform,
                "Python_Version": py_version,
            },
        ]

    def get_dependencies_side_effect(*args, **kwargs):
        platform = args[1]
        py_version = args[2]
        return [
            {
                "Name": "dep1.whl",
                "Version": "2.0.0",
                "Size_Bytes": 2000,
                "Type": "Dependency",
                "Platform": platform,
                "Python_Version": py_version,
            },
            {
                "Name": "dep2.whl",
                "Version": "2.0.0",
                "Size_Bytes": 1000,
                "Type": "Dependency",
                "Platform": platform,
                "Python_Version": py_version,
            },
        ]

    with (
        patch("ddev.cli.size.utils.common_funcs.GitRepo", return_value=fake_repo),
        patch(
            "ddev.cli.size.utils.common_funcs.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch(
            "ddev.cli.size.utils.common_funcs.get_valid_versions",
            return_value=({"3.12"}),
        ),
        patch("ddev.cli.size.utils.common_funcs.tempfile.mkdtemp", return_value="fake_repo"),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["linux-aarch64_3.12"]),
        patch(
            "ddev.cli.size.utils.common_funcs.get_files",
            side_effect=get_files_side_effect,
        ),
        patch(
            "ddev.cli.size.utils.common_funcs.get_dependencies",
            side_effect=get_dependencies_side_effect,
        ),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield


@pytest.mark.parametrize(
    "diff_args",
    [
        ["commit1", "--compare-to", "commit2"],
        ["commit1", "--compare-to", "commit2", "--compressed"],
        ["commit1", "--compare-to", "commit2", "--format", "csv,markdown,json,png"],
        ["commit1", "--compare-to", "commit2", "--show-gui"],
        ["commit1", "--compare-to", "commit2", "--platform", "linux-aarch64", "--python", "3.12"],
        ["commit1", "--compare-to", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"],
    ],
    ids=[
        "no options",
        "compressed",
        "all formats",
        "show gui",
        "with platform and version",
        "with platform, version and compressed",
    ],
)
def test_diff_options(ddev, mock_size_diff_dependencies, diff_args):
    result = ddev("size", "diff", *diff_args)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "diff_args",
    [
        ["commit1", "--compare-to", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"],
        ["commit1", "--compare-to", "commit2"],
        ["commit1", "--compare-to", "commit2", "--compressed"],
        ["commit1", "--compare-to", "commit2", "--format", "csv,markdown,json,png"],
        ["commit1", "--compare-to", "commit2", "--show-gui"],
    ],
    ids=[
        "platform, python and compressed",
        "no options",
        "compressed",
        "all formats",
        "show gui",
    ],
)
def test_diff_no_differences(ddev, mock_size_diff_no_diff_dependencies, diff_args):
    result = ddev("size", "diff", *diff_args)

    assert result.exit_code == 0, result.output
    assert "No size differences were detected" in result.output


@pytest.mark.parametrize(
    "first_commit, second_commit, format_list, platform, version, error_expected",
    [
        ("abcdefg", "bcdefgh", [], "invalid-platform", "3.9", "Invalid platform: invalid-platform"),
        ("abcdefg", "bcdefgh", [], "linux-x86_64", "invalid-version", "Invalid version: invalid-version"),
        (
            "abc",
            "bcd",
            [],
            "linux-x86_64",
            "3.9",
            True,
        ),
        (
            "abc",
            "bcdefgh",
            [],
            "linux-x86_64",
            "3.9",
            True,
        ),
        (
            "abcdefg",
            "bcd",
            [],
            "linux-x86_64",
            "3.9",
            True,
        ),
        ("abcdefg", "abcdefg", [], "linux-x86_64", "3.9", True),
        (
            "abcdefg",
            "bcdefgh",
            ["invalid-format"],
            "linux-x86_64",
            "3.9",
            True,
        ),
        (
            "abc",
            "abcdefg",
            ["invalid-format"],
            "invalid-platform",
            "3.9",
            True,
        ),
        ("abcdefg", "bcdefgh", ["png"], "linux-x86_64", "3.9", False),
        ("abcdefg", "bcdefgh", [], None, None, False),
    ],
    ids=[
        "invalid platform",
        "invalid version",
        "both commits too short",
        "first commit too short",
        "second commit too short",
        "same commits",
        "invalid format",
        "multiple errors",
        "valid parameters",
        "valid parameters without optional values",
    ],
)
def test_validate_parameters(first_commit, second_commit, format_list, platform, version, error_expected):
    valid_platforms = {"linux-x86_64", "windows-x86_64"}
    valid_versions = {"3.9", "3.11"}

    app = MagicMock()
    app.abort.side_effect = SystemExit

    if error_expected:
        with pytest.raises(SystemExit):
            validate_parameters(
                app, first_commit, second_commit, format_list, valid_platforms, valid_versions, platform, version
            )
        app.abort.assert_called_once()
    else:
        validate_parameters(
            app, first_commit, second_commit, format_list, valid_platforms, valid_versions, platform, version
        )
        app.abort.assert_not_called()
