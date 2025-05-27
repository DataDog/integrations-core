# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Generator

import pytest

from ddev.config.file import DDEV_TOML, ConfigFileWithOverrides
from ddev.utils.fs import Path
from ddev.utils.toml import dump_toml_data, load_toml_file
from tests.helpers.git import ClonedRepo
from tests.helpers.runner import CliRunner, Result


@pytest.fixture(autouse=True)
# Ensure the local override is removed from any test if we have generated it
def delete_local_override_config(config_file: ConfigFileWithOverrides):
    yield
    if config_file.overrides_available():
        config_file.overrides_path.unlink()


@pytest.fixture
def repo_with_ddev_tool_config(repository_as_cwd: ClonedRepo) -> Generator[ClonedRepo, None, None]:
    pyproject_path = repository_as_cwd.path / "pyproject.toml"
    pyproject = load_toml_file(pyproject_path)
    pyproject["tool"]["ddev"] = {"repo": "core"}
    dump_toml_data(pyproject, pyproject_path)

    yield repository_as_cwd


def test_create_new_overrides_config(
    ddev: CliRunner, config_file: ConfigFileWithOverrides, helpers, repo_with_ddev_tool_config: ClonedRepo
):
    temp_dir = repo_with_ddev_tool_config.path

    result = ddev("config", "override")
    local_path = str(temp_dir).replace("\\", "\\\\")

    expected_output = helpers.dedent(
        f"""
        Local repo configuration added in {config_file.pretty_overrides_path}

        Local config content:
        repo = "core"

        [repos]
        core = "{local_path}"
        """
    )
    # Reload new values
    config_file.load()

    assert result.exit_code == 0, result.output
    assert result.output == expected_output

    # Verify the config was actually created
    assert config_file.overrides_path.exists()
    assert config_file.overrides_model.raw_data["repos"]["core"] == str(config_file.overrides_path.parent)
    assert config_file.overrides_model.raw_data["repo"] == "core"


def test_update_existing_local_config(
    ddev: CliRunner, config_file: ConfigFileWithOverrides, helpers, repo_with_ddev_tool_config: ClonedRepo
):
    ddev_path = repo_with_ddev_tool_config.path / DDEV_TOML
    existing_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "test_key"

        [repos]
        core = "/old/path"
        """
    )
    ddev_path.write_text(existing_config)

    result = ddev("config", "override")
    local_path = str(ddev_path.parent).replace("\\", "\\\\")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Local config file already exists. Updating...
        Local repo configuration added in {config_file.pretty_overrides_path}

        Local config content:
        repo = "core"

        [orgs.default]
        api_key = "*****"

        [repos]
        core = "{local_path}"
        """
    )

    # Verify the config was updated correctly
    config_file.load()
    assert config_file.overrides_model.raw_data["repos"]["core"] == str(repo_with_ddev_tool_config.path)
    assert config_file.overrides_model.raw_data["repo"] == "core"
    assert config_file.overrides_model.raw_data["orgs"]["default"]["api_key"] == "test_key"


def assert_valid_local_config(
    config_file: ConfigFileWithOverrides, repo_path: Path, result: Result, expected_output: str
):
    assert result.exit_code == 0
    assert "The current repo could not be inferred" in result.output
    assert "What repo are you trying to override?" in result.output
    assert expected_output in result.output
    assert config_file.overrides_model.raw_data["repos"]["extras"] == str(repo_path)
    assert config_file.overrides_model.raw_data["repo"] == "extras"


def test_not_in_repo_ask_user(ddev: CliRunner, config_file: ConfigFileWithOverrides, helpers, overrides_config: Path):
    result = ddev("config", "override", input="extras")
    extras_path = str(config_file.overrides_path.parent).replace("\\", "\\\\")

    expected_output = helpers.dedent(
        f"""
        Local config file already exists. Updating...
        Local repo configuration added in {config_file.pretty_overrides_path}

        Local config content:
        repo = "extras"

        [repos]
        extras = "{extras_path}"
        """
    )
    # Reload new values
    config_file.load()
    assert_valid_local_config(config_file, overrides_config.parent, result, expected_output)


def test_pyproject_not_found_ask_user(
    ddev: CliRunner, config_file: ConfigFileWithOverrides, helpers, repository_as_cwd: ClonedRepo
):
    original_pyproject = repository_as_cwd.path / "pyproject.toml"
    backup_pyproject = original_pyproject.with_suffix(".bak")
    original_pyproject.rename(backup_pyproject)

    result = ddev("config", "override", input="extras")
    extras_path = str(config_file.overrides_path.parent).replace("\\", "\\\\")

    expected_output = helpers.dedent(
        f"""
        Local repo configuration added in {config_file.pretty_overrides_path}

        Local config content:
        repo = "extras"

        [repos]
        extras = "{extras_path}"
        """
    )

    # Reload new values
    config_file.load()
    assert_valid_local_config(config_file, config_file.overrides_path.parent, result, expected_output)

    # Restore the original pyproject.toml
    backup_pyproject.rename(original_pyproject)


def test_misconfigured_pyproject_fails(
    ddev: CliRunner, config_file: ConfigFileWithOverrides, repository_as_cwd: ClonedRepo
):
    # Setup wrongly configured pyproject.toml
    pyproject_path = repository_as_cwd.path / "pyproject.toml"
    pyproject = load_toml_file(pyproject_path)
    pyproject["tool"]["ddev"] = {"repo": "wrong-repo"}
    dump_toml_data(pyproject, pyproject_path)

    result = ddev("config", "override")
    assert result.exit_code == 1
    assert "Invalid ddev metadata found in pyproject.toml" in result.output
    assert "[tool.ddev.repo] is 'wrong-repo': Input should be 'core'" in result.output
