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
