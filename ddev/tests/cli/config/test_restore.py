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


def test_delete_local_overrides_yes(ddev, config_file, helpers):
    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )
    config_file.overrides_path.write_text(local_config)

    result = ddev('config', 'restore', input='y')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Settings were successfully restored.
        Overrides file found in '{config_file.overrides_path}'. Do you want to delete it? [y/N]: y
        Overrides deleted.
        """
    )
    assert not config_file.overrides_path.exists()


def test_delete_local_overrides_no(ddev, config_file, helpers):
    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )
    config_file.overrides_path.write_text(local_config)

    result = ddev('config', 'restore', input='n')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Settings were successfully restored.
        Overrides file found in '{config_file.overrides_path}'. Do you want to delete it? [y/N]: n
        """
    )
    assert config_file.overrides_path.exists()
