# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from unittest.mock import MagicMock, patch

import pytest


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


@pytest.fixture
def mock_size_diff_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

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
            "ddev.cli.size.diff.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.diff.get_valid_versions",
            return_value=({'3.12'}),
        ),
        patch("ddev.cli.size.diff.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.diff.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.diff.GitRepo.checkout_commit"),
        patch("tempfile.mkdtemp", return_value="fake_repo"),
        patch("ddev.cli.size.diff.get_files", side_effect=get_compressed_files_side_effect),
        patch("ddev.cli.size.diff.get_dependencies", side_effect=get_compressed_dependencies_side_effect),
        patch("ddev.cli.size.diff.format_modules", side_effect=lambda m, *_: m),
        patch("matplotlib.pyplot.show"),
        patch("matplotlib.pyplot.savefig"),
    ):
        yield


def test_diff_no_args(ddev, mock_size_diff_dependencies):
    assert ddev("size", "diff", "commit1", "commit2").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--compressed").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--csv").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--markdown").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--json").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--save_to_png_path", "out.png").exit_code == 0
    assert ddev("size", "diff", "commit1", "commit2", "--show_gui").exit_code == 0


def test_diff_with_platform_and_version(ddev, mock_size_diff_dependencies):
    assert ddev("size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12").exit_code == 0
    assert (
        ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"
        ).exit_code
        == 0
    )
    assert (
        ddev("size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--csv").exit_code
        == 0
    )
    assert (
        ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--markdown"
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--json"
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "diff",
            "commit1",
            "commit2",
            "--platform",
            "linux-aarch64",
            "--python",
            "3.12",
            "--save_to_png_path",
            "out.png",
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--show_gui"
        ).exit_code
        == 0
    )


def test_diff_no_differences(ddev):
    fake_repo = MagicMock()
    fake_repo.repo_dir = "fake_repo"
    fake_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.diff.GitRepo.__enter__", return_value=fake_repo),
        patch("ddev.cli.size.diff.GitRepo.__exit__", return_value=None),
        patch(
            "ddev.cli.size.diff.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.diff.get_valid_versions",
            return_value=({'3.12'}),
        ),
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
        patch("matplotlib.pyplot.show"),
        patch("matplotlib.pyplot.savefig"),
    ):
        result = ddev(
            "size", "diff", "commit1", "commit2", "--platform", "linux-aarch64", "--python", "3.12", "--compressed"
        )

        assert result.exit_code == 0, result.output
        assert "No size differences were detected" in result.output

        assert ddev("size", "diff", "commit1", "commit2").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--compressed").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--csv").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--markdown").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--json").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--save_to_png_path", "out.png").exit_code == 0
        assert ddev("size", "diff", "commit1", "commit2", "--show_gui").exit_code == 0


def test_diff_invalid_platform(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo
    with (
        patch("ddev.cli.size.diff.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
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
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
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
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
        ),
    ):
        result = ddev("size", "diff", "commit1", "commit2", "--platform", "linux", "--python", "2.10", "--compressed")
        assert result.exit_code != 0
