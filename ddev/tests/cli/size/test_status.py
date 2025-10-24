# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.size.status import validate_parameters
from ddev.cli.size.utils.size_model import Size, Sizes


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


@pytest.fixture()
def mock_size_status():
    fake_repo_path = Path(os.path.join("fake_root")).resolve()

    mock_walk = [(os.path.join(str(fake_repo_path), "datadog_checks", "my_check"), [], ["__init__.py"])]

    mock_app = MagicMock()
    mock_app.repo.path = fake_repo_path

    fake_files = Sizes(
        [
            Size(
                name="int1",
                version="1.1.1",
                size_bytes=1234,
                type="Integration",
                platform="linux-x86_64",
                python_version="3.12",
            )
        ]
    )

    fake_deps = Sizes(
        [
            Size(
                name="dep1",
                version="1.1.1",
                size_bytes=5678,
                type="Dependency",
                platform="linux-x86_64",
                python_version="3.12",
            )
        ]
    )

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
        ([]),
        (["--compressed"]),
        (["--format", "csv,markdown,json,png"]),
        (["--show-gui"]),
        (["--platform", "linux-aarch64", "--python", "3.12"]),
        (["--platform", "linux-aarch64", "--python", "3.12", "--compressed"]),
        (["--platform", "linux-aarch64", "--python", "3.12", "--format", "csv,markdown,json,png"]),
        (["--platform", "linux-aarch64", "--python", "3.12", "--format", "csv, markdown, json, png"]),
        (["--platform", "linux-aarch64", "--python", "3.12", "--show-gui"]),
    ],
    ids=[
        "no_args",
        "compressed",
        "format",
        "show_gui",
        "platform_and_version",
        "platform_version_compressed",
        "platform_version_format",
        "platform_version_format_with_spaces",
        "platform_version_show_gui",
    ],
)
def test_status(ddev, mock_size_status, args: list[str]):
    command = ["size", "status"] + args

    result = ddev(*command)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    (
        "platform",
        "version",
        "to_dd_org",
        "to_dd_key",
        "commit",
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
            None,  # to_dd_site
            False,  # should_abort
            id="valid",
        ),
        pytest.param(
            "invalid-platform",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            None,  # commit
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
            None,  # to_dd_site
            True,  # should_abort
            id="invalid_version",
        ),
        pytest.param(
            "linux-x86_64",  # platform
            "3.12",  # version
            None,  # to_dd_org
            None,  # to_dd_key
            "1234567890",  # commit
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
    to_dd_site: str | None,
    should_abort: bool,
    tmp_path: Path,
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
                to_dd_org,
                commit,
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
            to_dd_key,
            to_dd_site,
            app,
        )
        app.abort.assert_not_called()
