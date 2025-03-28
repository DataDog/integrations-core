# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock, mock_open, patch

import pytest

from ddev.cli.size.status import (
    get_compressed_dependencies,
    get_compressed_files,
)


def test_get_compressed_files():
    mock_files = [
        ("root/integration/datadog_checks", [], ["file1.py", "file2.py"]),
        ("root/integration_b/datadog_checks", [], ["file3.py"]),
        ("root", [], ["ignored.py"]),
    ]

    def fake_compress(file_path):
        return 1000

    fake_gitignore = {"ignored.py"}

    with (
        patch("os.walk", return_value=mock_files),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace("root/", "")),
        patch("ddev.cli.size.status.get_gitignore_files", return_value=fake_gitignore),
        patch(
            "ddev.cli.size.status.is_valid_integration",
            side_effect=lambda path, folder, ignored, git_ignore: path.startswith("integration"),
        ),
        patch("ddev.cli.size.status.compress", side_effect=fake_compress),
    ):

        result = get_compressed_files()

    expected = [
        {
            "File Path": "integration/datadog_checks/file1.py",
            "Type": "Integration",
            "Name": "integration",
            "Size (Bytes)": 1000,
        },
        {
            "File Path": "integration/datadog_checks/file2.py",
            "Type": "Integration",
            "Name": "integration",
            "Size (Bytes)": 1000,
        },
        {
            "File Path": "integration_b/datadog_checks/file3.py",
            "Type": "Integration",
            "Name": "integration_b",
            "Size (Bytes)": 1000,
        },
    ]

    assert result == expected


def test_get_compressed_dependencies():
    platform = "windows-x86_64"
    version = "3.12"

    fake_file_content = (
        "dependency1 @ https://example.com/dependency1.whl\ndependency2 @ https://example.com/dependency2.whl"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": "12345"}

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[f"{platform}-{version}"]),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_file_content)),
        patch("requests.head", return_value=mock_response),
    ):

        file_data = get_compressed_dependencies(platform, version)

    assert file_data == [
        {"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345},
        {"File Path": "dependency2", "Type": "Dependency", "Name": "dependency2", "Size (Bytes)": 12345},
    ]


@pytest.fixture()
def mock_size_status():
    with (
        patch("ddev.cli.size.status.get_gitignore_files", return_value=set()),
        patch("ddev.cli.size.status.compress", return_value=1234),
        patch("ddev.cli.size.status.get_dependencies", return_value=(["dep1"], {"dep1": "https://example.com/dep1"})),
        patch(
            "ddev.cli.size.status.get_dependencies_sizes",
            return_value=[
                {"File Path": "dep1.whl", "Type": "Dependency", "Name": "dep1", "Size (Bytes)": 5678},
            ],
        ),
        patch("ddev.cli.size.status.is_valid_integration", return_value=True),
        patch("ddev.cli.size.status.is_correct_dependency", return_value=True),
        patch("ddev.cli.size.status.print_csv"),
        patch("ddev.cli.size.status.print_table"),
        patch(
            "os.walk",
            return_value=[
                ("datadog_checks/my_check", [], ["__init__.py"]),
            ],
        ),
        patch("os.listdir", return_value=["fake_dep.whl"]),
        patch("os.path.isfile", return_value=True),
    ):
        yield


def test_status_no_args(ddev, mock_size_status):
    result = ddev('size', 'status', '--compressed')
    assert result.exit_code == 0


def test_status(ddev, mock_size_status):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '3.12', '--compressed')
    assert result.exit_code == 0


def test_status_csv(ddev, mock_size_status):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '3.12', '--compressed', '--csv')
    assert result.exit_code == 0


def test_status_wrong_platform(ddev):
    result = ddev('size', 'status', '--platform', 'linux', '--python', '3.12', '--compressed')
    assert result.exit_code != 0


def test_status_wrong_version(ddev):
    result = ddev('size', 'status', '--platform', 'linux-aarch64', '--python', '2.10', '--compressed')
    assert result.exit_code != 0


def test_status_wrong_plat_and_version(ddev):
    result = ddev('size', 'status', '--platform', 'linux', '--python', '2.10', '--compressed')
    assert result.exit_code != 0
