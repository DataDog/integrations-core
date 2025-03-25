# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock, mock_open, patch

from ddev.cli.size.diff import get_compressed_dependencies, get_compressed_files, get_diff


def test_get_compressed_files():
    mock_app = MagicMock()
    mock_repo_path = "root"

    mock_files = [
        ("root/integration/datadog_checks", [], ["file1.py", "file2.py"]),
        ("root/integration_b/datadog_checks", [], ["file3.py"]),
        ("root", [], ["ignored.py"]),
    ]

    def fake_compress(app, file_path, relative_path):
        return 1000

    fake_gitignore = {"ignored.py"}

    with (
        patch("os.walk", return_value=mock_files),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace("root/", "")),
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data="__pycache__/\n*.log\n")),
        patch("ddev.cli.size.diff.get_gitignore_files", return_value=fake_gitignore),
        patch(
            "ddev.cli.size.diff.is_valid_integration",
            side_effect=lambda path, folder, ignored, git_ignore: path.startswith("integration"),
        ),
        patch("ddev.cli.size.diff.compress", side_effect=fake_compress),
    ):

        result = get_compressed_files(mock_app, mock_repo_path)

    expected = {
        "integration/datadog_checks/file1.py": 1000,
        "integration/datadog_checks/file2.py": 1000,
        "integration_b/datadog_checks/file3.py": 1000,
    }

    assert result == expected


def test_get_compressed_dependencies(terminal):
    platform = "windows-x86_64"
    version = "3.12"

    fake_file_content = (
        "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}
    mock_repo_path = "root"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[f"{platform}-{version}"]),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_file_content)),
        patch("requests.head", return_value=mock_response),
    ):

        file_data = get_compressed_dependencies(terminal, mock_repo_path, platform, version)

    assert file_data == {
        "dependency1": 12345,
        "dependency2": 12345,
    }

    def test_get_diff():
        size_before = {
            "integration/foo.py": 1000,
            "integration/bar.py": 2000,
            "integration/deleted.py": 1500,
        }
        size_after = {
            "integration/foo.py": 1200,  # modified
            "integration/bar.py": 2000,  # unchanged
            "integration/new.py": 800,  # new
        }

        expected = [
            {
                "File Path": "integration/foo.py",
                "Type": "Integration",
                "Name": "integration",
                "Size (Bytes)": 200,
            },
            {
                "File Path": "integration/deleted.py",
                "Type": "Integration",
                "Name": "integration (DELETED)",
                "Size (Bytes)": -1500,
            },
            {
                "File Path": "integration/new.py",
                "Type": "Integration",
                "Name": "integration (NEW)",
                "Size (Bytes)": 800,
            },
        ]

        result = get_diff(size_before, size_after, "Integration")
        assert sorted(result, key=lambda x: x["File Path"]) == sorted(expected, key=lambda x: x["File Path"])
