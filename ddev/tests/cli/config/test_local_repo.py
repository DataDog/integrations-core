# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.file import RootConfig
from ddev.utils.toml import load_toml_data


def test_create_new_local_config(ddev, config_file, helpers):
    result = ddev('config', 'local-repo')

    expected_output = helpers.dedent(
        f"""
        Local repo configuration added in {config_file.local_path}
        Local config content:
        repo = "local"

        [repos]
        local = "{config_file.local_path.parent}"
        """
    )

    assert result.exit_code == 0, result.output
    assert result.output == expected_output

    # Verify the config was actually created
    assert config_file.local_path.exists()
    local_config = RootConfig(load_toml_data(config_file.local_path.read_text()))
    assert local_config.raw_data['repos']['local'] == str(config_file.local_path.parent)
    assert local_config.raw_data['repo'] == 'local'


def test_update_existing_local_config(ddev, config_file, helpers):
    """Test updating an existing local config file while preserving other settings."""
    # Create an existing local config with some settings
    existing_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "test_key"

        [repos]
        local = "/old/path"
        """
    )
    config_file.local_path.write_text(existing_config)

    result = ddev('config', 'local-repo')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Local config file already exists. Updating...
        Local repo configuration added in {config_file.local_path}
        Local config content:
        repo = "local"

        [orgs.default]
        api_key = "*****"

        [repos]
        local = "{config_file.local_path.parent}"
        """
    )

    # Verify the config was updated correctly
    local_config = RootConfig(load_toml_data(config_file.local_path.read_text()))
    assert local_config.raw_data['repos']['local'] == str(config_file.local_path.parent)
    assert local_config.raw_data['repo'] == 'local'
    assert local_config.raw_data['orgs']['default']['api_key'] == 'test_key'
