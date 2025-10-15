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
        patch("ddev.cli.size.utils.files.get_gitignore_files", return_value=set()),
        patch(
            "ddev.cli.size.utils.general.get_valid_platforms",
            return_value=({'linux-x86_64', 'macos-x86_64', 'linux-aarch64', 'macos-aarch64', 'windows-x86_64'}),
        ),
        patch(
            "ddev.cli.size.utils.general.get_valid_versions",
            return_value=({'3.12'}),
        ),
        patch("ddev.cli.size.utils.files.get_files", return_value=fake_files),
        patch("ddev.cli.size.utils.dependencies.get_dependencies", return_value=fake_deps),
        patch("ddev.cli.size.utils.files.os.walk", return_value=mock_walk),
        patch("ddev.cli.size.utils.dependencies.os.listdir", return_value=["fake_dep.whl"]),
        patch("ddev.cli.size.utils.dependencies.os.path.isfile", return_value=True),
    ):
        yield mock_app


@pytest.mark.parametrize(
    "args, use_dependency_sizes",
    [
        ([], False),
        (["--compressed"], False),
        (["--format", "csv,markdown,json,png"], False),
        (["--show-gui"], False),
        (["--platform", "linux-aarch64", "--python", "3.12"], False),
        (["--platform", "linux-aarch64", "--python", "3.12", "--compressed"], False),
        (["--platform", "linux-aarch64", "--python", "3.12", "--format", "csv,markdown,json,png"], False),
        (["--platform", "linux-aarch64", "--python", "3.12", "--show-gui"], False),
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
def test_status(ddev, mock_size_status, tmp_path, args, use_dependency_sizes):
    command = ["size", "status"] + args

    if use_dependency_sizes:
        fake_deps = [
            {
                "Name": "dep1",
                "Version": "1.1.1",
                "Size_Bytes": 5678,
                "Size": 123,
                "Type": "Dependency",
                "Platform": "linux-aarch64",
                "Python_Version": "3.12",
            }
        ]
        dependency_sizes_file = tmp_path / "sizes"
        dependency_sizes_file.write_text("{}")
        command.extend(["--dependency-sizes", str(dependency_sizes_file)])

        with patch("ddev.cli.size.utils.dependencies.get_dependencies_from_json", return_value=fake_deps):
            result = ddev(*command)
            assert result.exit_code == 0
    else:
        result = ddev(*command)
        assert result.exit_code == 0


@pytest.mark.parametrize(
    (
        "platform",
        "version",
        "to_dd_org",
        "to_dd_key",
        "commit",
        "dependency_sizes_path",
        "create_dependency_sizes_file",
        "to_dd_site",
        "should_abort",
    ),
    [
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            False,  # should_abort
            id="valid_simple",
        ),
        pytest.param(
            "macos-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            "1234567890abcdef1234567890abcdef12345678",  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            False,  # should_abort
            id="valid_with_commit",
        ),
        pytest.param(
            "linux-aarch64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            Path("sizes"),  # dependency_sizes_path
            True,  # create_dependency_sizes_file
            None,  # to_dd_site
            False,  # should_abort
            id="valid_with_dependency_sizes",
        ),
        pytest.param(
            "invalid-platform",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="invalid_platform",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "2.7",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="invalid_version",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            Path("sizes"),  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="invalid_dependency_sizes_file",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            "1234567890123456789012345678901234567890",  # commit
            Path("sizes"),  # dependency_sizes_path
            True,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            "1234567890",  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="invalid_commit",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            "test-org",  # to_dd_org
            "test-key",  # to_dd_key
            None,  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="to_dd_org_and_to_dd_key",
        ),
        pytest.param(
            "invalid-platform",  # platform
            "2.7",  # version
            "test-org",  # to_dd_org
            "test-key",  # to_dd_key
            "1234567890",  # commit
            Path("sizes"),  # dependency_sizes_path
            True,  # create_dependency_sizes_file
            None,  # to_dd_site
            True,  # should_abort
            id="multiple_errors",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
            None,  # dependency_sizes_path
            False,  # create_dependency_sizes_file
            "test-site",  # to_dd_site
            True,  # should_abort
            id="to_dd_site_and_not_to_dd_key",
        ),
    ],
)
def test_validate_parameters(
    platform: str | None,
    version: str | None,
    to_dd_org: str | None,
    to_dd_key: str | None,
    commit: str | None,
    dependency_sizes_path: str | None,
    create_dependency_sizes_file: bool,
    to_dd_site: str | None,
    should_abort: bool,
    tmp_path: Path,
):
    valid_platforms = ["linux-x86_64", "macos-x86_64", "linux-aarch64", "macos-aarch64", "windows-x86_64"]
    valid_versions = ["3.12"]

    dependency_sizes = None
    if dependency_sizes_path:
        dependency_sizes = tmp_path / dependency_sizes_path
        if create_dependency_sizes_file:
            dependency_sizes.touch()

    app = MagicMock()
    app.abort.side_effect = SystemExit

    if should_abort:
        with pytest.raises(SystemExit):
            validate_parameters(
                valid_platforms,
                valid_versions,
                platform,
                version,
                to_dd_org,
                commit,
                dependency_sizes,
                to_dd_key,
                to_dd_site,
                app,
            )
        app.abort.assert_called_once()
    else:
        validate_parameters(
            valid_platforms,
            valid_versions,
            platform,
            version,
            to_dd_org,
            commit,
            dependency_sizes,
            to_dd_key,
            to_dd_site,
            app,
        )
        app.abort.assert_not_called()
