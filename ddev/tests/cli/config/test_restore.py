# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def test_standard(ddev, config_file):
    config_file.model.repo = 'marketplace'
    config_file.save()

    result = ddev('config', 'restore')

    assert result.exit_code == 0, result.output
    assert result.output == 'Settings were successfully restored.\n'

    config_file.load()
    assert config_file.model.repo.name == 'core'


def test_allow_invalid_config(ddev, config_file, helpers):
    config_file.model.agent = ['foo']
    config_file.save()

    result = ddev('config', 'restore')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Settings were successfully restored.
        """
    )


def test_delete_local_overrides_yes(ddev, config_file, helpers, overrides_config):
    print(f"Overrides exists: {overrides_config.exists()}")
    print(f"Overrides is file: {overrides_config.is_file()}")
    print(f"Overrides path: {overrides_config}")
    result = ddev('config', 'restore', input='y')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Settings were successfully restored.
        Overrides file found in '{overrides_config}'. Do you want to delete it? [y/N]: y
        Overrides deleted.
        """
    )
    assert not overrides_config.exists()


def test_delete_local_overrides_no(ddev, config_file, helpers, overrides_config):
    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )
    overrides_config.write_text(local_config)

    result = ddev('config', 'restore', input='n')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Settings were successfully restored.
        Overrides file found in '{config_file.overrides_path}'. Do you want to delete it? [y/N]: n
        """
    )
    assert config_file.overrides_path.exists()
