# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def test_standard(ddev, config_file, helpers):
    result = ddev('config', 'set', 'repo', 'marketplace')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        repo = "marketplace"
        """
    )

    config_file.load()
    assert config_file.model.repo.name == 'marketplace'


def test_standard_deep(ddev, config_file, helpers):
    result = ddev('config', 'set', 'orgs.default.site', 'foo')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        [orgs.default]
        site = "foo"
        """
    )

    config_file.load()
    assert config_file.model.orgs['default']['site'] == 'foo'


def test_standard_complex(ddev, config_file, helpers):
    result = ddev('config', 'set', 'agents.latest', "{'docker': 'datadog/agent:latest', 'local': 'latest'}")

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        [agents.latest]
        docker = "datadog/agent:latest"
        local = "latest"
        """
    )

    config_file.load()
    assert config_file.model.agents['latest'] == {'docker': 'datadog/agent:latest', 'local': 'latest'}


def test_standard_hidden(ddev, config_file, helpers):
    result = ddev('config', 'set', 'orgs.foo.api_key', 'bar')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        [orgs.foo]
        api_key = "*****"
        """
    )

    config_file.load()
    assert config_file.model.orgs['foo'] == {'api_key': 'bar'}


def test_prompt(ddev, config_file, helpers):
    result = ddev('config', 'set', 'repo', input='marketplace')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Value for `repo`: marketplace
        New setting:
        repo = "marketplace"
        """
    )

    config_file.load()
    assert config_file.model.repo.name == 'marketplace'


def test_prompt_hidden(ddev, config_file, helpers):
    result = ddev('config', 'set', 'orgs.foo.api_key', input='bar')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Value for `orgs.foo.api_key`:{' '}
        New setting:
        [orgs.foo]
        api_key = "*****"
        """
    )

    config_file.load()
    assert config_file.model.orgs['foo'] == {'api_key': 'bar'}


def test_prevent_invalid_config(ddev, config_file, helpers):
    original_repo = config_file.model.repo.name
    result = ddev('config', 'set', 'repo', '["foo"]')

    assert result.exit_code == 1
    assert result.output == helpers.dedent(
        """
        Error parsing config:
        repo
          must be a string
        """
    )

    config_file.load()
    assert config_file.model.repo.name == original_repo


def test_resolve_repo_path(ddev, config_file, helpers, temp_dir):
    with temp_dir.as_cwd():
        result = ddev('config', 'set', 'repos.core', '.')

    path = str(temp_dir).replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        New setting:
        [repos]
        core = "{path}"
        """
    )

    config_file.load()
    assert config_file.model.repo.path == str(temp_dir)


def test_local_standard(ddev, config_file, helpers):
    result = ddev('config', 'set', '--local', 'repo', 'marketplace')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        repo = "marketplace"
        """
    )

    # Verify it was written to the local config file
    config_file.load()
    assert config_file.local_path.exists()
    assert config_file.local_model.repo.name == 'marketplace'
    # Global config should remain unchanged
    assert config_file.global_model.repo.name != 'marketplace'


def test_local_validates_combined_config(ddev, config_file, helpers):
    # First set an invalid type in global config
    config_file.global_model.raw_data['agents'] = 'invalid'
    config_file.save()

    # Try to set a valid config in local file
    result = ddev('config', 'set', '--local', 'repo', 'marketplace')

    # Should fail because the combined config is invalid
    assert result.exit_code == 1
    assert 'Error parsing config' in result.output


def test_global_standard(ddev, config_file, helpers):
    # First set a value in local config
    result = ddev('config', 'set', 'repo', 'extras', '--local')
    assert result.exit_code == 0

    # Then set a different value in global config
    result = ddev('config', 'set', 'repo', 'marketplace')
    assert result.exit_code == 0

    config_file.load()
    # Local config should keep its value
    assert config_file.local_model.repo.name == 'extras'
    # Global config should have the new value
    assert config_file.global_model.repo.name == 'marketplace'
    # Combined config should use local value
    assert config_file.combined_model.repo.name == 'extras'
