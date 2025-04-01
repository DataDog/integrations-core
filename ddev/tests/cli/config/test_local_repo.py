# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def test_create_new_overrides_config(ddev, config_file, helpers, temp_dir):
    with temp_dir.as_cwd():
        result = ddev('config', 'local-repo')
        local_path = str(temp_dir).replace('\\', '\\\\')

        expected_output = helpers.dedent(
            f"""
            Local repo configuration added in {config_file.pretty_overrides_path}
            Local config content:
            repo = "local"

            [repos]
            local = "{local_path}"
            """
        )
        # Reload new values
        config_file.load()

        assert result.exit_code == 0, result.output
        assert result.output == expected_output

        # Verify the config was actually created
        assert config_file.overrides_path.exists()
        assert config_file.overrides_model.raw_data['repos']['local'] == str(config_file.overrides_path.parent)
        assert config_file.overrides_model.raw_data['repo'] == 'local'


def test_update_existing_local_config(ddev, config_file, helpers, overrides_config):
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
    overrides_config.write_text(existing_config)

    result = ddev('config', 'local-repo')
    local_path = str(config_file.overrides_path.parent).replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Local config file already exists. Updating...
        Local repo configuration added in {config_file.pretty_overrides_path}
        Local config content:
        repo = "local"

        [orgs.default]
        api_key = "*****"

        [repos]
        local = "{local_path}"
        """
    )

    # Verify the config was updated correctly
    config_file.load()
    assert config_file.overrides_model.raw_data['repos']['local'] == str(config_file.overrides_path.parent)
    assert config_file.overrides_model.raw_data['repo'] == 'local'
    assert config_file.overrides_model.raw_data['orgs']['default']['api_key'] == 'test_key'
