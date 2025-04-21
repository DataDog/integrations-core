from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ddev.cli.size.timeline import (
    format_commit_data,
    get_dependencies,
    get_dependency,
    get_dependency_size,
    get_files,
    get_version,
    group_modules,
    trim_modules,
)


def test_get_compressed_files():
    with (
        patch("os.walk", return_value=[("/tmp/fake_repo/int1", [], ["int1.py"])]),
        patch("os.path.relpath", return_value="int1/int1.py"),
        patch("os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.is_valid_integration", return_value=True),
        patch("ddev.cli.size.timeline.compress", return_value=1234),
    ):
        result = get_files(
            "/tmp/fake_repo", "int1", "abc1234", datetime(2025, 4, 4).date(), "auth", "Added int1", [], True
        )
        assert result == [
            {
                "Size (Bytes)": 1234,
                "Date": datetime(2025, 4, 4).date(),
                "Author": "auth",
                "Commit Message": "Added int1",
                "Commit SHA": "abc1234",
            }
        ]


def test_get_compressed_files_deleted_only():
    repo_path = "/tmp/fake_repo"
    module = "foo"
    commit = "abc1234"
    date = datetime.strptime("Apr 5 2025", "%b %d %Y").date()
    author = "Author"
    message = "deleted module"

    with (
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("os.walk", return_value=[]),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace(f"{repo_path}/", "")),
        patch("os.path.exists", return_value=False),
    ):
        file_data = get_files(repo_path, module, commit, date, author, message, [], True)

    assert file_data == [
        {
            "Size (Bytes)": 0,
            "Date": date,
            "Author": author,
            "Commit Message": "(DELETED) " + message,
            "Commit SHA": commit,
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
        {"Size (Bytes)": 1000},
        {"Size (Bytes)": 1100},  # diff = 100 -> should be removed if threshold = 200
        {"Size (Bytes)": 1400},  # diff = 300 -> should be kept
    ]
    expected = [
        {"Size (Bytes)": 1000, "Delta (Bytes)": 0, "Delta": " "},
        {"Size (Bytes)": 1400, "Delta (Bytes)": 300, "Delta": "300 B"},
    ]
    trimmed = trim_modules(modules, threshold=200)
    assert trimmed == expected


def test_group_modules():
    modules = [
        {
            "Size (Bytes)": 1000,
            "Date": datetime(2025, 4, 4).date(),
            "Author": "A",
            "Commit Message": "msg",
            "Commit SHA": "c1",
        },
        {
            "Size (Bytes)": 500,
            "Date": datetime(2025, 4, 4).date(),
            "Author": "A",
            "Commit Message": "msg",
            "Commit SHA": "c1",
        },
        {
            "Size (Bytes)": 1500,
            "Date": datetime(2025, 4, 5).date(),
            "Author": "A",
            "Commit Message": "msg2",
            "Commit SHA": "c2",
        },
    ]
    expected = [
        {
            "Commit SHA": "c1",
            "Size (Bytes)": 1500,
            "Size": "1.46 KB",
            "Delta (Bytes)": "N/A",
            "Delta": "N/A",
            "Date": datetime(2025, 4, 4).date(),
            "Author": "A",
            "Commit Message": "msg",
            "Platform": "linux-x86_64",
        },
        {
            "Commit SHA": "c2",
            "Size (Bytes)": 1500,
            "Size": "1.46 KB",
            "Delta (Bytes)": "N/A",
            "Delta": "N/A",
            "Date": datetime(2025, 4, 5).date(),
            "Author": "A",
            "Commit Message": "msg2",
            "Platform": "linux-x86_64",
        },
    ]
    grouped = group_modules(modules, "linux-x86_64", 0)
    assert grouped == expected


def test_get_dependency():
    content = """dep1 @ https://example.com/dep1.whl
dep2 @ https://example.com/dep2.whl"""
    with patch("builtins.open", mock_open(read_data=content)):
        url = get_dependency("some/path/file.txt", "dep2")
        assert url == "https://example.com/dep2.whl"


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
            "https://example.com/file.whl", "abc1234", datetime(2025, 4, 4).date(), "auth", "Fixed bug", True
        )
        assert info == {
            "Size (Bytes)": 45678,
            "Date": datetime(2025, 4, 4).date(),
            "Author": "auth",
            "Commit Message": "Fixed bug",
            "Commit SHA": "abc1234",
        }


def test_get_compressed_dependencies():
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.listdir", return_value=["linux-x86_64_3.12.txt"]),
        patch("ddev.cli.size.timeline.get_dependency", return_value="https://example.com/dep1.whl"),
        patch("ddev.cli.size.timeline.requests.head", return_value=make_mock_response("12345")),
    ):
        result = get_dependencies(
            "/tmp/fake_repo", "dep1", "linux-x86_64", "abc1234", datetime(2025, 4, 4).date(), "auth", "Added dep1", True
        )
        assert result == {
            "Size (Bytes)": 12345,
            "Date": datetime(2025, 4, 4).date(),
            "Author": "auth",
            "Commit Message": "Added dep1",
            "Commit SHA": "abc1234",
        }


@pytest.fixture
def mock_timeline_gitrepo():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "/tmp/fake_repo"
    mock_git_repo.get_module_commits.return_value = ["commit1", "commit2"]
    mock_git_repo.get_creation_commit_module.return_value = "commit1"
    mock_git_repo.get_commit_metadata.side_effect = lambda c: ("Apr 4 2025", "Initial commit", c)

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.GitRepo.sparse_checkout_commit"),
        patch("ddev.cli.size.timeline.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.compress", return_value=1234),
        patch("os.walk", return_value=[("/tmp/fake_repo/int", [], ["file1.py"])]),
        patch("os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.group_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.print_table"),
        patch("ddev.cli.size.timeline.print_csv"),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.listdir", return_value=["linux-x86_64_3.12_dep1.whl", "linux-x86_64_3.12_dep2.whl"]),
    ):
        yield


@pytest.fixture
def app():
    mock_app = MagicMock()
    mock_app.repo.path = "/tmp/fake_repo"
    return mock_app


def test_timeline_integration_compressed(ddev, mock_timeline_gitrepo, app):
    result = ddev("size", "timeline", "integration", "int1", "commit1", "commit2", "--compressed", obj=app)
    assert result.exit_code == 0


@pytest.fixture
def mock_timeline_dependencies():
    mock_git_repo = MagicMock()
    mock_git_repo.repo_dir = "/tmp/fake_repo"
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
        patch("ddev.cli.size.timeline.get_dependency", return_value="https://example.com/dep1.whl"),
        patch("ddev.cli.size.timeline.requests.head") as mock_head,
        patch("ddev.cli.size.timeline.group_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.trim_modules", side_effect=lambda m, *_: m),
        patch("ddev.cli.size.timeline.print_table"),
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
    mock_git_repo.repo_dir = "/tmp/fake_repo"
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
    mock_git_repo.repo_dir = "/tmp/fake_repo"
    mock_git_repo.get_module_commits.return_value = [""]

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_git_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
    ):
        result = ddev("size", "timeline", "integration", "integration/foo", "commit1", "commit2", "--compressed")
        assert result.exit_code != 0
        assert "No changes found" in result.output


def test_timeline_integration_not_found(ddev):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "/fake"
    mock_repo.get_module_commits.return_value = [""]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch(
            "ddev.cli.size.timeline.valid_platforms_versions",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'windows-x86_64'}, {'3.12'}),
        ),
        patch("ddev.cli.size.timeline.module_exists", return_value=False),
    ):
        result = ddev("size", "timeline", "integration", "missing_module", "c1", "c2")
        assert result.exit_code != 0
        assert "not found" in result.output


def test_timeline_dependency_missing_no_platform(ddev):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "/fake"
    mock_repo.get_module_commits.return_value = ["c1"]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None

    with (
        patch("ddev.cli.size.timeline.GitRepo.__enter__", return_value=mock_repo),
        patch("ddev.cli.size.timeline.GitRepo.__exit__", return_value=None),
        patch("ddev.cli.size.timeline.valid_platforms_versions", return_value=({"linux-x86_64"}, {"3.12"})),
        patch("ddev.cli.size.timeline.get_dependency_list", return_value=set()),
    ):
        result = ddev("size", "timeline", "dependency", "missing_module", "c1", "c2")
        assert result.exit_code != 0
        assert "Dependency missing_module not found in latest commit" in result.output


def test_timeline_dependency_missing_for_platform(ddev, app):
    mock_repo = MagicMock()
    mock_repo.repo_dir = "/fake"
    mock_repo.get_module_commits.return_value = ["c1"]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None

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
            "c1",
            "c2",
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
    mock_repo.repo_dir = "/fake"
    mock_repo.get_module_commits.return_value = [""]
    mock_repo.get_creation_commit_module.return_value = "c1"
    mock_repo.checkout_commit.return_value = None

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
            "c1",
            "c2",
            "--platform",
            "linux-x86_64",
            obj=app,
        )

        assert result.exit_code != 0
        assert "no changes found" in result.output.lower()
