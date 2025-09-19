# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.file import DDEV_TOML
from ddev.utils.fs import Path


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
    assert config_file.model.agents["latest"] == {"docker": "datadog/agent:latest", "local": "latest"}


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
        Value for `orgs.foo.api_key`:{" "}
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

    path = str(temp_dir).replace("\\", "\\\\")

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


def test_overrides_standard(ddev, config_file, helpers, overrides_config):
    result = ddev('config', 'set', '--overrides', 'repo', 'marketplace')
    # Verify it was written to the overrides config file
    config_file.load()

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        New setting:
        repo = "marketplace"
        """
    )

    assert config_file.overrides_available()
    assert config_file.overrides_model.repo.name == "marketplace"
    # Global config should remain unchanged
    assert config_file.global_model.repo.name != "marketplace"


def test_overrides_validates_combined_config(ddev, config_file, overrides_config):
    # First set an invalid type in global config
    config_file.global_model.raw_data["agents"] = "invalid"
    config_file.save()

    # Try to set a valid config in overrides file
    result = ddev('config', 'set', '--overrides', 'repo', 'marketplace')

    config_file.load()

    # Should fail because the combined config is invalid
    assert result.exit_code == 1
    assert "Error parsing config" in result.output


def test_global_standard(ddev, config_file, overrides_config):
    # First set a value in overrides config
    result = ddev('config', 'set', 'repo', 'extras', '--overrides')
    assert result.exit_code == 0, result.output

    # Then set a different value in global config
    result = ddev('config', 'set', 'repo', 'marketplace')
    assert result.exit_code == 0, result.output

    config_file.load()

    # Overrides config should keep its value
    assert config_file.overrides_model.repo.name == 'extras'
    # Global config should have the new value
    assert config_file.global_model.repo.name == 'marketplace'
    # Combined config should use overrides value
    assert config_file.combined_model.repo.name == 'extras'


def test_overrides_creates_file(ddev, config_file, helpers, temp_dir):
    with temp_dir.as_cwd():
        overrides_config = Path.cwd() / DDEV_TOML
        result = ddev('config', 'set', '--overrides', 'repo', 'marketplace', input='y')

    assert result.exit_code == 0, result.output
    assert 'No overrides file found, would you like to create one in the current directory?' in result.output
    assert result.output.endswith(
        helpers.dedent(
            """
            New setting:
            repo = "marketplace"
            """
        )
    )

    # Verify the file was created and contains the correct value
    config_file.overrides_path = overrides_config
    config_file.load()
    assert config_file.overrides_available()
    assert config_file.overrides_model.repo.name == 'marketplace'
    # Global config should remain unchanged
    assert config_file.global_model.repo.name != 'marketplace'


def test_overrides_no_create_file(ddev, config_file):
    result = ddev('config', 'set', '--overrides', 'repo', 'marketplace', input='n')

    assert result.exit_code == 1
    assert 'No overrides file found, would you like to create one in the current directory?' in result.output
    assert 'No overrides file found and no permission to create one.' in result.output

    # Verify the file was not created
    assert not config_file.overrides_path.is_file()
