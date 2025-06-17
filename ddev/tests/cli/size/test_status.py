# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


@pytest.fixture()
def mock_size_status():
    fake_repo_path = Path(os.path.join("fake_root")).resolve()

    mock_walk = [(os.path.join(str(fake_repo_path), "datadog_checks", "my_check"), [], ["__init__.py"])]

    mock_app = MagicMock()
    mock_app.repo.path = fake_repo_path

    fake_files = [
        {
            "Name": "int1",
            "Version": "1.1.1",
            "Size_Bytes": 1234,
            "Size": 100,
            "Type": "Integration",
        }
    ]

    fake_deps = [
        {
            "Name": "dep1",
            "Version": "1.1.1",
            "Size_Bytes": 5678,
            "Size": 123,
            "Type": "Dependency",
        }
    ]

    with (
        patch("ddev.cli.size.utils.common_funcs.get_gitignore_files", return_value=set()),
        patch(
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
        ),
        patch("ddev.cli.size.status.get_files", return_value=fake_files),
        patch("ddev.cli.size.status.get_dependencies", return_value=fake_deps),
        patch(
            "ddev.cli.size.utils.common_funcs.os.path.relpath",
            side_effect=lambda path, _: path.replace(f"fake_root{os.sep}", ""),
        ),
        patch("ddev.cli.size.utils.common_funcs.compress", return_value=1234),
        patch("ddev.cli.size.utils.common_funcs.os.walk", return_value=mock_walk),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["fake_dep.whl"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.plt.show"),
        patch("ddev.cli.size.utils.common_funcs.plt.savefig"),
        patch("ddev.cli.size.utils.common_funcs.plt.figure"),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield mock_app


def test_status_no_args(ddev, mock_size_status):
    assert ddev("size", "status").exit_code == 0
    assert ddev("size", "status", "--compressed").exit_code == 0
    assert ddev("size", "status", "--format", "csv,markdown,json,png").exit_code == 0
    assert ddev("size", "status", "--show-gui").exit_code == 0


def test_status(ddev, mock_size_status):
    assert (ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12")).exit_code == 0
    assert (ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12", "--compressed")).exit_code == 0
    assert (
        ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12", "--format", "csv,markdown,json,png")
    ).exit_code == 0
    assert (ddev("size", "status", "--platform", "linux-aarch64", "--python", "3.12", "--show-gui")).exit_code == 0


def test_status_wrong_platform(ddev):
    with (
        patch(
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
        ),
    ):
        result = ddev("size", "status", "--platform", "linux", "--python", "3.12", "--compressed")
        assert result.exit_code != 0


def test_status_wrong_version(ddev):
    with (
        patch(
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
        ),
    ):
        result = ddev("size", "status", "--platform", "linux-aarch64", "--python", "2.10", "--compressed")
        assert result.exit_code != 0


def test_status_wrong_plat_and_version(ddev):
    with (
        patch(
            "ddev.cli.size.status.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.status.get_valid_versions",
            return_value=({'3.12'}),
        ),
    ):
        result = ddev("size", "status", "--platform", "linux", "--python", "2.10", "--compressed")
        assert result.exit_code != 0
