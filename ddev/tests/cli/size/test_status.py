# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ddev.cli.size.status import (
    get_dependencies,
    get_files,
)


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


def test_get_files_compressed():
    mock_files = [
        (os.path.join("root", "integration", "datadog_checks"), [], ["file1.py", "file2.py"]),
        (os.path.join("root", "integration_b", "datadog_checks"), [], ["file3.py"]),
        ("root", [], ["ignored.py"]),
    ]
    mock_repo_path = "root"

    def fake_compress(file_path):
        return 1000

    fake_gitignore = {"ignored.py"}

    with (
        patch("os.walk", return_value=mock_files),
        patch("os.path.relpath", side_effect=lambda path, _: path.replace(f"root{os.sep}", "")),
        patch("ddev.cli.size.status.get_gitignore_files", return_value=fake_gitignore),
        patch(
            "ddev.cli.size.status.is_valid_integration",
            side_effect=lambda path, folder, ignored, git_ignore: path.startswith("integration"),
        ),
        patch("ddev.cli.size.status.compress", side_effect=fake_compress),
    ):
        result = get_files(True, mock_repo_path)

    expected = [
        {
            "File Path": to_native_path("integration/datadog_checks/file1.py"),
            "Type": "Integration",
            "Name": "integration",
            "Size (Bytes)": 1000,
        },
        {
            "File Path": to_native_path("integration/datadog_checks/file2.py"),
            "Type": "Integration",
            "Name": "integration",
            "Size (Bytes)": 1000,
        },
        {
            "File Path": to_native_path("integration_b/datadog_checks/file3.py"),
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
    mock_repo_path = "root"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[f"{platform}-{version}"]),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_file_content)),
        patch("requests.head", return_value=mock_response),
    ):
        file_data = get_dependencies(mock_repo_path, platform, version, True)

    assert file_data == [
        {"File Path": "dependency1", "Type": "Dependency", "Name": "dependency1", "Size (Bytes)": 12345},
        {"File Path": "dependency2", "Type": "Dependency", "Name": "dependency2", "Size (Bytes)": 12345},
    ]


@pytest.fixture()
def mock_size_status():
    fake_repo_path = Path(os.path.join("fake_root")).resolve()

    mock_walk = [(os.path.join(str(fake_repo_path), "datadog_checks", "my_check"), [], ["__init__.py"])]

    mock_app = MagicMock()
    mock_app.repo.path = fake_repo_path

    with (
        patch("ddev.cli.size.status.get_gitignore_files", return_value=set()),
        patch(
            "ddev.cli.size.status.valid_platforms_versions",
            return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
        ),
        patch("ddev.cli.size.status.compress", return_value=1234),
        patch(
            "ddev.cli.size.status.get_dependencies_list", return_value=(["dep1"], {"dep1": "https://example.com/dep1"})
        ),
        patch(
            "ddev.cli.size.status.get_dependencies_sizes",
            return_value=[{"File Path": "dep1.whl", "Type": "Dependency", "Name": "dep1", "Size (Bytes)": 5678}],
        ),
        patch("ddev.cli.size.status.is_valid_integration", return_value=True),
        patch("ddev.cli.size.status.is_correct_dependency", return_value=True),
        patch("ddev.cli.size.status.print_csv"),
        patch("ddev.cli.size.status.print_table"),
        patch("ddev.cli.size.status.plot_treemap"),
        patch("os.walk", return_value=mock_walk),
        patch("os.listdir", return_value=["fake_dep.whl"]),
        patch("os.path.isfile", return_value=True),
    ):
        yield mock_app


def test_status_no_args(ddev, mock_size_status):
    result = ddev("size", "status", "--compressed")
    assert result.exit_code == 0


def test_status(ddev, mock_size_status):
    result = ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12", "--compressed")
    print(result.output)
    assert result.exit_code == 0


def test_status_csv(ddev, mock_size_status):
    result = ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12", "--compressed", "--csv")
    print(result.output)
    assert result.exit_code == 0


def test_status_wrong_platform(ddev):
    with patch(
        "ddev.cli.size.timeline.valid_platforms_versions",
        return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
    ):
        result = ddev("size", "status", "--platform", "linux", "--python", "3.12", "--compressed")
        assert result.exit_code != 0


def test_status_wrong_version(ddev):
    with patch(
        "ddev.cli.size.timeline.valid_platforms_versions",
        return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
    ):
        result = ddev("size", "status", "--platform", "linux-aarch64", "--python", "2.10", "--compressed")
        assert result.exit_code != 0


def test_status_wrong_plat_and_version(ddev):
    with patch(
        "ddev.cli.size.timeline.valid_platforms_versions",
        return_value=({"linux-x86_64", "macos-x86_64", "linux-aarch64", "windows-x86_64"}, {"3.12"}),
    ):
        result = ddev("size", "status", "--platform", "linux", "--python", "2.10", "--compressed")
        assert result.exit_code != 0
