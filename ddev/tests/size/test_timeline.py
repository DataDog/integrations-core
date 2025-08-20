import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from ddev.cli.size.timeline import (
    format_commit_data,
    get_dependencies,
    get_dependency_data,
    get_dependency_size,
    get_files,
    get_version,
    trim_modules,
)


def test_get_compressed_files():
    with (
        patch(
            "ddev.cli.size.timeline.os.walk",
            return_value=[(os.path.join("fake_repo", "datadog_checks"), [], ["__about__.py"])],
        ),
        patch("ddev.cli.size.timeline.os.path.relpath", return_value=os.path.join("datadog_checks", "__about__.py")),
        patch("ddev.cli.size.timeline.os.path.exists", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.is_valid_integration_file", return_value=True),
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
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.timeline.os.walk", return_value=[]),
        patch(
            "ddev.cli.size.timeline.os.path.relpath",
            side_effect=lambda path, _: path.replace(f"{repo_path}{os.sep}", ""),
        ),
        patch("ddev.cli.size.timeline.os.path.exists", return_value=False),
    ):
        file_data = get_files(repo_path, module, commit, date, author, message, [], True)

    assert file_data == [
        {
            "Size_Bytes": 0,
            "Version": "Deleted",
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
    expected_message = "(NEW) this is a very long commit...(#1234)"
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
        {"Size_Bytes": 1000, "Delta_Bytes": 0, "Delta": " ", "Version": "1.0.0"},
        {"Size_Bytes": 1400, "Delta_Bytes": 300, "Delta": "300 B", "Version": "1.0.0 -> 1.1.0"},
    ]
    trimmed = trim_modules(modules, threshold=200)
    assert trimmed == expected


def test_get_dependency():
    content = """dep1 @ https://example.com/dep1/dep1-1.1.1-.whl
dep2 @ https://example.com/dep2/dep2-1.1.2-.whl"""
    with patch("ddev.cli.size.timeline.open", mock_open(read_data=content)):
        url, version = get_dependency_data(Path("some") / "path" / "file.txt", "dep2")
        assert (url, version) == ("https://example.com/dep2/dep2-1.1.2-.whl", "1.1.2")


def make_mock_response(size):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.headers = {"Content-Length": size}
    mock_response.raise_for_status = lambda: None
    return mock_response


def test_get_dependency_size():
    mock_response = make_mock_response("45678")
    with patch("ddev.cli.size.timeline.requests.head", return_value=mock_response):
        info = get_dependency_size(
            "https://example.com/dep1/dep1-1.1.1-.whl",
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
        patch("ddev.cli.size.timeline.os.path.exists", return_value=True),
        patch("ddev.cli.size.timeline.os.path.isdir", return_value=True),
        patch("ddev.cli.size.timeline.os.path.isfile", return_value=True),
        patch("ddev.cli.size.timeline.os.listdir", return_value=["linux-x86_64_3.12.txt"]),
        patch(
            "ddev.cli.size.timeline.get_dependency_data",
            return_value=("https://example.com/dep1/dep1-1.1.1-.whl", '1.1.1'),
        ),
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
