# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.size.common import convert_size
from ddev.cli.size.diff import get_diff


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


"""
def test_get_compressed_files():
    mock_repo_path = "root"

    mock_files = [
        (os.path.join("root", "integration", "datadog_checks"), [], ["file1.py", "file2.py"]),
        (os.path.join("root", "integration_b", "datadog_checks"), [], ["file3.py"]),
        ("root", [], ["ignored.py"]),
    ]

    def fake_compress(file_path):
        return 1000

    fake_gitignore = {"ignored.py"}

    with (
        patch("os.walk", return_value=mock_files),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace(f"root{os.sep}", "")),
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data="__pycache__/\n*.log\n")),
        patch("ddev.cli.size.diff.get_gitignore_files", return_value=fake_gitignore),
        patch(
            "ddev.cli.size.diff.is_valid_integration",
            side_effect=lambda path, folder, ignored, git_ignore: path.startswith("integration"),
        ),
        patch("ddev.cli.size.diff.compress", side_effect=fake_compress),
    ):

        result = get_files(mock_repo_path, True)

    expected = {
        to_native_path("integration/datadog_checks/file1.py"): 1000,
        to_native_path("integration/datadog_checks/file2.py"): 1000,
        to_native_path("integration_b/datadog_checks/file3.py"): 1000,
    }

    assert result == expected


def test_get_compressed_dependencies(terminal):
    platform = "windows-x86_64"
    version = "3.12"

    fake_file_content = (
        "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    )

    mock_head_response = MagicMock()
    mock_head_response.status_code = 200
    mock_head_response.headers = {"Content-Length": "12345"}

    mock_get_response = MagicMock()
    mock_get_response.__enter__.return_value = mock_get_response  # for use in `with` block
    mock_get_response.status_code = 200
    mock_get_response.headers = {"Content-Length": "12345"}
    mock_get_response.content = b"Fake wheel file content"

    mock_repo_path = "root"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[f"{platform}-{version}"]),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_file_content)),
        patch("requests.head", return_value=mock_head_response),
        patch("requests.get", return_value=mock_get_response),
    ):
        file_data = get_dependencies(mock_repo_path, platform, version, True)

    assert file_data == {
        "dependency1": 12345,
        "dependency2": 12345,
    }

"""


def test_get_diff():
    size_before = [
        {"Name": "foo", "Version": "1.0.0", "Size_Bytes": 1000, "Type": "Integration"},
        {"Name": "bar", "Version": "2.0.0", "Size_Bytes": 2000, "Type": "Integration"},
        {"Name": "deleted", "Version": "3.0.0", "Size_Bytes": 1500, "Type": "Integration"},
    ]

    size_after = [
        {"Name": "foo", "Version": "1.1.0", "Size_Bytes": 1200, "Type": "Integration"},
        {"Name": "bar", "Version": "2.0.0", "Size_Bytes": 2000, "Type": "Integration"},
        {"Name": "new", "Version": "0.1.0", "Size_Bytes": 800, "Type": "Integration"},
    ]

    result = get_diff(size_before, size_after, "Integration")

    expected = [
        {
            "Name": "deleted (DELETED)",
            "Version": "3.0.0",
            "Type": "Integration",
            "Size_Bytes": -1500,
            "Size": convert_size(-1500),
        },
        {
            "Name": "foo",
            "Version": "1.0.0 -> 1.1.0",
            "Type": "Integration",
            "Size_Bytes": 200,
            "Size": convert_size(200),
        },
        {
            "Name": "new (NEW)",
            "Version": "0.1.0",
            "Type": "Integration",
            "Size_Bytes": 800,
            "Size": convert_size(800),
        },
    ]

    assert sorted(result, key=lambda x: x["Name"]) == expected


@pytest.fixture
def mock_size_diff_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"

    def get_compressed_files_side_effect(_, __):
        get_compressed_files_side_effect.counter += 1
        if get_compressed_files_side_effect.counter % 2 == 1:
            return [{"Name": "path1.py", "Version": "1.1.1", "Size_Bytes": 1000, "Type": "Integration"}]  # before
        else:
            return [
                {"Name": "path1.py", "Version": "1.1.2", "Size_Bytes": 1200, "Type": "Integration"},
                {"Name": "path2.py", "Version": "1.1.1", "Size_Bytes": 500, "Type": "Integration"},
            ]  # after

    get_compressed_files_side_effect.counter = 0

    def get_compressed_dependencies_side_effect(_, __, ___, ____):
        get_compressed_dependencies_side_effect.counter += 1
        if get_compressed_dependencies_side_effect.counter % 2 == 1:
            return [{"Name": "dep1", "Version": "1.0.0", "Size_Bytes": 2000, "Type": "Dependency"}]  # before
        else:
            return [
                {"Name": "dep1", "Version": "1.1.0", "Size_Bytes": 2500, "Type": "Dependency"},
                {"Name": "dep2", "Version": "1.0.0", "Size_Bytes": 1000, "Type": "Dependency"},
            ]  # after

    get_compressed_dependencies_side_effect.counter = 0

    with (
        patch(
            "ddev.cli.size.diff.valid_platforms_versions",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
        ),
        patch("ddev.cli.size.diff.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.diff.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.diff.GitRepo.checkout_commit"),
        patch("tempfile.mkdtemp", return_value="fake_repo"),
        patch("ddev.cli.size.diff.get_files", side_effect=get_compressed_files_side_effect),
        patch("ddev.cli.size.diff.get_dependencies", side_effect=get_compressed_dependencies_side_effect),
        patch("ddev.cli.size.diff.group_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.common.print_csv"),
        patch("ddev.cli.size.common.print_table"),
        patch("ddev.cli.size.common.plot_treemap"),
    ):
        yield


def test_diff_no_args(ddev, mock_size_diff_dependencies):
    result = ddev("size", "diff", "commit1", "commit2", "--compressed")
    assert result.exit_code == 0


def test_diff_with_platform_and_version(ddev, mock_size_diff_dependencies):
    result = ddev(
        "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"
    )
    assert result.exit_code == 0


def test_diff_csv(ddev, mock_size_diff_dependencies):
    result = ddev(
        "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed", "--csv"
    )
    assert result.exit_code == 0


def test_diff_no_differences(ddev):
    fake_repo = MagicMock()
    fake_repo.repo_dir = "fake_repo"

    with (
        patch("ddev.cli.size.diff.GitRepo.__enter__", return_value=fake_repo),
        patch("ddev.cli.size.diff.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.diff.valid_platforms_versions", return_value=({"linux-aarch64"}, {"3.12"})),
        patch.object(fake_repo, "checkout_commit"),
        patch("tempfile.mkdtemp", return_value="fake_repo"),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.listdir", return_value=["linux-aarch64_3.12"]),
        patch(
            "ddev.cli.size.diff.get_files",
            return_value=[
                {"Name": "path1.py", "Version": "1.0.0", "Size_Bytes": 1000},
                {"Name": "path2.py", "Version": "1.0.0", "Size_Bytes": 500},
            ],
        ),
        patch(
            "ddev.cli.size.diff.get_dependencies",
            return_value=[
                {"Name": "dep1.whl", "Version": "2.0.0", "Size_Bytes": 2000},
                {"Name": "dep2.whl", "Version": "2.0.0", "Size_Bytes": 1000},
            ],
        ),
    ):
        result = ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"
        )

        print(result.output)
        assert result.exit_code == 0, result.output
        assert "No size differences were detected" in result.output


def test_diff_invalid_platform(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo
    with (
        patch("ddev.cli.size.diff.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
        ),
    ):
        result = ddev("size", "diff", "commit1", "commit2", "--platform", "linux", "--python", "3.12", "--compressed")
        assert result.exit_code != 0


def test_diff_invalid_version(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo

    with (
        patch("ddev.cli.size.diff.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
        ),
    ):
        result = ddev(
            "size",
            "diff",
            "commit1",
            "commit2",
            "--platform",
            "linux-aarch64",
            "--python",
            "2.10",  # invalid
            "--compressed",
        )
        assert result.exit_code != 0


def test_diff_invalid_platform_and_version(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo
    with (
        patch("ddev.cli.size.diff.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
        ),
    ):
        result = ddev("size", "diff", "commit1", "commit2", "--platform", "linux", "--python", "2.10", "--compressed")
        assert result.exit_code != 0
