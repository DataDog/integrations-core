# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.size.status import validate_parameters


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
            "ddev.cli.size.utils.common_funcs.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.utils.common_funcs.get_valid_versions",
            return_value=({'3.12'}),
        ),
        patch("ddev.cli.size.utils.common_funcs.get_files", return_value=fake_files),
        patch("ddev.cli.size.utils.common_funcs.get_dependencies", return_value=fake_deps),
        patch(
            "ddev.cli.size.utils.common_funcs.os.path.relpath",
            side_effect=lambda path, _: path.replace(f"fake_root{os.sep}", ""),
        ),
        patch("ddev.cli.size.utils.common_funcs.compress", return_value=1234),
        patch("ddev.cli.size.utils.common_funcs.os.walk", return_value=mock_walk),
        patch("ddev.cli.size.utils.common_funcs.os.listdir", return_value=["fake_dep.whl"]),
        patch("ddev.cli.size.utils.common_funcs.os.path.isfile", return_value=True),
        patch("ddev.cli.size.utils.common_funcs.open", MagicMock()),
    ):
        yield mock_app


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--compressed"],
        ["--format", "csv,markdown,json,png"],
        ["--show-gui"],
        ["--platform", "linux-aarch64", "--python", "3.12"],
        ["--platform", "linux-aarch64", "--python", "3.12", "--compressed"],
        ["--platform", "linux-aarch64", "--python", "3.12", "--format", "csv,markdown,json,png"],
        ["--platform", "linux-aarch64", "--python", "3.12", "--show-gui"],
    ],
    ids=[
        "no_args",
        "compressed",
        "format",
        "show_gui",
        "platform_and_version",
        "platform_version_compressed",
        "platform_version_format",
        "platform_version_show_gui",
    ],
)
def test_status(ddev, mock_size_status, args):
    result = ddev(*["size", "status"] + args)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    (
        "platform",
        "version",
        "format",
        "to_dd_org",
        "to_dd_key",
        "commit",
        "branch",
        "declared",
        "should_abort",
    ),
    [
        # Valid cases
        ("linux-x86_64", "3.12", ["csv"], None, None, None, None, False, False),
        ("macos-x86_64", "3.12", [], None, None, "abc123", None, False, False),
        ("linux-aarch64", "3.12", [], None, None, "abc123", None, True, False),
        # Invalid platform
        ("invalid-platform", "3.12", [], None, None, None, None, False, True),
        # Invalid version
        ("linux-x86_64", "2.7", [], None, None, None, None, False, True),
        # --declared without --commit
        ("linux-x86_64", "3.12", [], None, None, None, None, True, True),
        # --to-dd-key without --commit
        ("linux-x86_64", "3.12", [], None, "test-key", None, "main", False, True),
        # --to-dd-key without --branch
        ("linux-x86_64", "3.12", [], None, "test-key", "abc123", None, False, True),
        # Invalid format
        ("linux-x86_64", "3.12", ["invalid-format"], None, None, None, None, False, True),
        # Both to_dd_org and to_dd_key
        ("linux-x86_64", "3.12", [], "test-org", "test-key", None, None, False, True),
        # Multiple errors
        ("invalid-platform", "2.7", ["invalid-format"], "test-org", "test-key", None, None, False, True),
    ],
    ids=[
        "valid_simple",
        "valid_with_commit",
        "valid_with_declared",
        "invalid_platform",
        "invalid_version",
        "declared_without_commit",
        "to_dd_key_without_commit",
        "to_dd_key_without_branch",
        "invalid_format",
        "to_dd_org_and_to_dd_key",
        "multiple_errors",
    ],
)
def test_validate_parameters(
    platform,
    version,
    format,
    to_dd_org,
    to_dd_key,
    commit,
    branch,
    declared,
    should_abort,
):
    valid_platforms = ["linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"]
    valid_versions = ["3.12"]

    app = MagicMock()
    app.abort.side_effect = SystemExit

    if should_abort:
        with pytest.raises(SystemExit):
            validate_parameters(
                valid_platforms,
                valid_versions,
                platform,
                version,
                format,
                to_dd_org,
                commit,
                to_dd_key,
                branch,
                declared,
                app,
            )
        app.abort.assert_called_once()
    else:
        validate_parameters(
            valid_platforms,
            valid_versions,
            platform,
            version,
            format,
            to_dd_org,
            commit,
            to_dd_key,
            branch,
            declared,
            app,
        )
        app.abort.assert_not_called()
