# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.file import DDEV_TOML


def test_call(ddev, config_file, mocker):
    mock = mocker.patch("click.edit")
    result = ddev("config", "edit")

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(filename=str(config_file.path))


def test_call_overrides(ddev, config_file, mocker, temp_dir, overrides_config):
    mock = mocker.patch("click.edit")

    # Ensure overrides path exist
    (temp_dir / DDEV_TOML).touch()

    result = ddev("config", "edit", "--overrides")

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(filename=str(overrides_config))


def test_call_overrides_no_file(ddev):
    result = ddev("config", "edit", "--overrides")

    assert result.exit_code == 1, result.output
    assert "No local config file found." in result.output
