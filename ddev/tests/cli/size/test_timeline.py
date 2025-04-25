import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ddev.cli.size.timeline import (
    format_commit_data,
    get_dependencies,
    get_dependency,
    get_dependency_size,
    get_files,
    get_version,
    trim_modules,
)


def test_get_compressed_files():
    with (
        patch("os.walk", return_value=[(os.path.join("fake_repo", "datadog_checks"), [], ["__about__.py"])]),
        patch("os.path.relpath", return_value=os.path.join("datadog_checks", "__about__.py")),
        patch("os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.is_valid_integration", return_value=True),
        patch("ddev.cli.size.timeline.compress", return_value=1234),
        patch("ddev.cli.size.timeline.extract_version_from_about_py", return_value='1.1.1'),
    ):
        result = get_files("fake_repo", "int1", "abc1234", datetime(2025, 4, 4).date(), "auth", "Added int1", [], True)
        print(result)
        assert result == [
            {
                "Size_Bytes": 1234,
                "Version": '1.1.1',
                "Date": datetime(2025, 4, 4).date(),
                "Author": "auth",
                "Commit_Message": "Added int1",
                "Commit_SHA": "abc1234",
            }
        ]


def test_get_compressed_files_deleted_only():
    repo_path = "fake_repo"
    module = "foo"
    commit = "abc1234"
    date = datetime.strptime("Apr 5 2025", "%b %d %Y").date()
    author = "Author"
    message = "deleted module"

    with (
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("os.walk", return_value=[]),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace(f"{repo_path}{os.sep}", "")),
        patch("os.path.exists", return_value=False),
    ):
        file_data = get_files(repo_path, module, commit, date, author, message, [], True)

    assert file_data == [
        {
            "Size_Bytes": 0,
            "Version": "",
            "Date": date,
            "Author": author,
            "Commit_Message": "(DELETED) " + message,
            "Commit_SHA": commit,
        }
    ]


def test_get_version():
    files = ["linux-x86_64_3.12.txt", "linux-x86_64_3.10.txt"]
    version = get_version(files, "linux-x86_64")
    assert version == "3.12"


def test_format_commit_data():
    date, message, commit = format_commit_data(
        "Apr 4 2025", "this is a very long commit message that should be trimmed (#1234)", "abc1234def", "abc1234def"
    )
    expected_date = datetime.strptime("Apr 4 2025", "%b %d %Y").date()
    expected_message = "(NEW) this is a very long...(#1234)"
    expected_commit = "abc1234"
    assert date == expected_date
    assert message == expected_message
    assert commit == expected_commit


def test_trim_modules_keep_some_remove_some():
    modules = [
        {"Size_Bytes": 1000, "Version": "1.0.0"},
        {"Size_Bytes": 1100, "Version": "1.0.0"},
        {"Size_Bytes": 1400, "Version": "1.1.0"},
    ]
    expected = [
        {"Size_Bytes": 1000, "Delta (Bytes)": 0, "Delta": " ", "Version": "1.0.0"},
        {"Size_Bytes": 1400, "Delta (Bytes)": 300, "Delta": "300 B", "Version": "1.0.0 -> 1.1.0"},
    ]
    trimmed = trim_modules(modules, threshold=200)
    assert trimmed == expected


def test_get_dependency():
    content = """dep1 @ https://example.com/dep1-1.1.1-.whl
dep2 @ https://example.com/dep2-1.1.2-.whl"""
    with patch("builtins.open", mock_open(read_data=content)):
        url, version = get_dependency(Path("some") / "path" / "file.txt", "dep2")
        assert (url, version) == ("https://example.com/dep2-1.1.2-.whl", "1.1.2")


def make_mock_response(size):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.headers = {"Content-Length": size}
    mock_response.raise_for_status = lambda: None
    return mock_response


def test_get_dependency_size():
    mock_response = make_mock_response("45678")
    with patch("requests.head", return_value=mock_response):
        info = get_dependency_size(
            "https://example.com/file-1.1.1-.whl",
            "1.1.1",
            "abc1234",
            datetime(2025, 4, 4).date(),
            "auth",
            "Fixed bug",
            True,
        )
        assert info == {
            "Size_Bytes": 45678,
            "Version": "1.1.1",
            "Date": datetime(2025, 4, 4).date(),
            "Author": "auth",
            "Commit_Message": "Fixed bug",
            "Commit_SHA": "abc1234",
        }


def test_get_compressed_dependencies():
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.listdir", return_value=["linux-x86_64_3.12.txt"]),
        patch("ddev.cli.size.timeline.get_dependency", return_value=("https://example.com/dep1.whl", '1.1.1')),
        patch("ddev.cli.size.timeline.requests.head", return_value=make_mock_response("12345")),
    ):
        result = get_dependencies(
            "fake_repo", "dep1", "linux-x86_64", "abc1234", datetime(2025, 4, 4).date(), "auth", "Added dep1", True
        )
        assert result == {
            "Size_Bytes": 12345,
            "Version": '1.1.1',
            "Date": datetime(2025, 4, 4).date(),
            "Author": "auth",
            "Commit_Message": "Added dep1",
            "Commit_SHA": "abc1234",
        }


@pytest.fixture
def mock_timeline_gitrepo():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_creation_commit_module.return_value = "commit1"
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Initial commit", c)

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.GitRepo.sparse_checkout_commit"),
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.compress", return_value=1234),
        patch("os.walk", return_value=[(Path("/tmp") / "fake_repo" / "int", [], ["file1.py"])]),
        patch("os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.group_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.print_table"),
        patch("ddev.cli.size.timeline.print_csv"),
        patch("ddev.cli.size.timeline.plot_linegraph"),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.listdir", return_value=["linux-x86_64_3.12_dep1.whl", "linux-x86_64_3.12_dep2.whl"]),
    ):
        yield


@pytest.fixture
def app():
    mock_app = MagicMock()
    mock_app.repo.path = "fake_repo"
    return mock_app


def test_timeline_integration_compressed(ddev, mock_timeline_gitrepo, app):
    result = ddev("size", "timeline", "integration", "int1", "commit1", "commit2", "--compressed", obj=app)
    assert result.exit_code == 0


@pytest.fixture
def mock_timeline_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.GitRepo.sparse_checkout_commit"),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}, {'3.12'}),
        ),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value={"dep1"}),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=["linux-x86_64-3.12"]),
        patch("os.path.isfile", return_value=True),
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.get_dependency", return_value=("https://example.com/dep1.whl", '1.1.1)')),
        patch("ddev.cli.size.timeline.requests.head") as mock_head,
        patch("ddev.cli.size.timeline.group_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.print_table"),
        patch("ddev.cli.size.timeline.plot_linegraph"),
    ):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "1024"}
        mock_response.raise_for_status = lambda: None
        mock_head.return_value = mock_response

        yield


def test_timeline_dependency_compressed(ddev, mock_timeline_dependencies, app):
    result = ddev(
        "size",
        "timeline",
        "dependency",
        "dep1",
        "commit1",
        "commit2",
        "--compressed",
        "--platform",
        "linux-x86_64",
        obj=app,
    )

    assert result.exit_code == 0


def test_timeline_invalid_platform(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Fix dep", c)
    mock_git_repo.__enter__.return_value = mock_git_repo

    with (
        patch("ddev.cli.size.timeline.GitRepo", return_value=mock_git_repo),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({'linux-x86_64', 'linux-aarch64', 'macos-x86_64'}, {'3.12'}),
        ),
    ):

        result = ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "commit1",
            "commit2",
            "--compressed",
            "--platform",
            "invalid-platform",
        )

    assert result.exit_code != 0


def test_timeline_no_changes_in_integration(ddev):
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "fake_repo"
    mock_git_repo.get_module_commits.return_value = [""]
    mock_git_repo.get_commit_metadata.return_value = ("Feb 1 2025", "", "")

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=("", "")),
    ):
        result = ddev("size", "timeline", "integration", "int1", "commit1", "commit2", "--compressed")
        assert result.exit_code != 0
        assert "No changes found" in result.output


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
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=("", "")),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}, {'3.12'}),
        ),
        patch("ddev.cli.size.timeline.module_exists", return_value=False),
    ):
        result = ddev("size", "timeline", "integration", "missing_module", "c123456", "c2345667")
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
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=({"linux-x86_64"}, {"3.12"})),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value=set()),
    ):
        result = ddev("size", "timeline", "dependency", "missing_module", "c123456", "c2345667")
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
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=({"linux-x86_64"}, {"3.12"})),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value=set()),
    ):

        result = ddev(
            "size",
            "timeline",
            "dependency",
            "missing_module",
            "c123456",
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
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=({"linux-x86_64"}, {"3.12"})),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value={"dep1"}),
    ):

        result = ddev(
            "size",
            "timeline",
            "dependency",
            "dep1",
            "c123456",
            "c2345667",
            "--platform",
            "linux-x86_64",
            obj=app,
        )

        assert result.exit_code != 0
        assert "no changes found" in result.output.lower()
