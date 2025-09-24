from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_timeline():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_creation_commit_module.return_value = "commit1"
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Initial commit", c)

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.GitRepo.sparse_checkout_commit"),
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.compress", return_value=1234),
        patch("ddev.cli.size.timeline.os.walk", return_value=[(Path("/tmp") / "fake_repo" / "int", [], ["file1.py"])]),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.format_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield


@pytest.fixture
def app():
    mock_app = MagicMock()
    mock_app.repo.path = "fake_repo"
    return mock_app


def test_timeline_integration(ddev, mock_timeline, app):
    assert (
        ddev(
            "size",
            "timeline",
            "integration",
            "int1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--compressed",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "integration",
            "int1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--format",
            "csv,markdown,json,png",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "integration",
            "int1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--show-gui",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "integration",
            "int1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--threshold",
            "1000",
            obj=app,
        ).exit_code
        == 0
    )


@pytest.fixture
def mock_timeline_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.get_creation_commit_module.side_effect = "initial_commit"
    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.GitRepo.sparse_checkout_commit"),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_.utils.common_funcs.64", "linux-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value={"dep1"}),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["linux-x86_64-3.12"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch(
            "ddev.cli.size.timeline.get_dependencies",
            return_value={
                "Size_Bytes": 12345,
                "Version": "1.2.3",
                "Date": date(2025, 4, 4),
                "Author": "Mock User",
                "Commit_Message": "Mock commit message",
                "Commit_SHA": "abcdef123456",
            },
        ),
        patch("ddev.cli.size.timeline.format_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield


def test_timeline_dependency(ddev, mock_timeline_dependencies, app):
    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--platform",
            "linux-x86_64",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--platform",
            "linux-x86_64",
            "--compressed",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--platform",
            "linux-x86_64",
            "--format",
            "csv,markdown,json,png",
            obj=app,
        ).exit_code
        == 0
    )

    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--platform",
            "linux-x86_64",
            "--show-gui",
            obj=app,
        ).exit_code
        == 0
    )
    assert (
        ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--platform",
            "linux-x86_64",
            "--threshold",
            "1000",
            obj=app,
        ).exit_code
        == 0
    )


def test_timeline_invalid_platform(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo

    with (
        patch("ddev.cli.size.timeline.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
    ):
        result = ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "commit1",
            "--final-commit",
            "commit2",
            "--compressed",
            "--platform",
            "invalid-platform",
        )

    assert result.exit_code != 0


def test_timeline_integration_no_changes(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = [""]
    mock_git_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=[]),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
    ):
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                )
            ).output
            and result.exit_code == 0
        )
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                    "--compressed",
                )
            ).output
            and result.exit_code == 0
        )
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                    "--format",
                    "csv,markdown,json,png",
                )
            ).output
            and result.exit_code == 0
        )
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                    "--show-gui",
                )
            ).output
            and result.exit_code == 0
        )
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                    "--threshold",
                    "1000",
                )
            ).output
            and result.exit_code == 0
        )
        assert (
            "No changes found"
            in (
                result := ddev(
                    "size",
                    "timeline",
                    "integration",
                    "int1",
                    "--initial-commit",
                    "commit1",
                    "--final-commit",
                    "commit2",
                    "--threshold",
                    "1000",
                )
            ).output
            and result.exit_code == 0
        )


def test_timeline_integration_not_found(ddev):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "fake"
    mock_repo.get_module_commits.return_value = [""]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None
    mock_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.timeline.module_exists", return_value=False),
    ):
        result = ddev(
            "size",
            "timeline",
            "integration",
            "missing_module",
            "--initial-commit",
            "c123456",
            "--final-commit",
            "c2345667",
        )
        assert result.exit_code != 0
        assert "not found" in result.output


def test_timeline_dependency_missing_no_platform(ddev):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "fake"
    mock_repo.get_module_commits.return_value = ["c1"]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None
    mock_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.utils.common_funcs.get_valid_versions", return_value={"3.12"}),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value=set()),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["linux-x86_64-3.12"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        result = ddev(
            "size",
            "timeline",
            "dependency",
            "missing_module",
            "--initial-commit",
            "c123456",
            "--final-commit",
            "c2345667",
        )
        assert result.exit_code != 0
        assert "Dependency missing_module not found in latest commit" in result.output


def test_timeline_dependency_missing_for_platform(ddev, app):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "fake"
    mock_repo.get_module_commits.return_value = ["c1"]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None
    mock_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.utils.common_funcs.get_valid_versions", return_value={"3.12"}),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value=set()),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["linux-x86_64-3.12"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        result = ddev(
            "size",
            "timeline",
            "dependency",
            "missing_module",
            "--initial-commit",
            "c123456",
            "--final-commit",
            "c2345667",
            "--platform",
            "linux-x86_64",
        )

        assert result.exit_code != 0
        assert (
            "Dependency missing_module not found in latest commit for the platform linux-x86_64, is the name correct?"
            in result.output
        )


def test_timeline_dependency_no_changes(ddev, app):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "fake"
    mock_repo.get_module_commits.return_value = [""]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None
    mock_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.utils.common_funcs.get_valid_versions", return_value={"3.12"}),
        patch(
            "ddev.cli.size.timeline.get_valid_platforms",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"}),
        ),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value={"dep1"}),
        patch("ddev.cli.size.utils.common_funcs.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.path.isdir", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["linux-x86_64-3.12"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        result = ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "--initial-commit",
            "c123456",
            "--final-commit",
            "c2345667",
            "--platform",
            "linux-x86_64",
            obj=app,
        )
        assert result.exit_code == 0
        assert "no changes found" in result.output.lower()
