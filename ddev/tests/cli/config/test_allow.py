# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from ddev.config.override_trust import TRUSTED_OVERRIDES_FILENAME


def test_allow_writes_allowed_entry(ddev, config_file, overrides_config):
    """Running `ddev config allow` writes an 'allowed' trust record for .ddev.toml."""
    overrides_config.write_text('[github]\nuser_fetch_command = "echo me"\n')

    result = ddev('config', 'allow')

    assert result.exit_code == 0, result.output
    assert 'Trusted' in result.output

    trust_file = config_file.global_path.parent / TRUSTED_OVERRIDES_FILENAME
    assert trust_file.is_file()

    store = json.loads(trust_file.read_text())
    key = str(overrides_config)
    assert key in store
    assert store[key]['state'] == 'allowed'
    assert 'hash' in store[key]


def test_allow_is_idempotent(ddev, config_file, overrides_config):
    """Calling `ddev config allow` twice does not raise an error."""
    overrides_config.write_text('[github]\nuser_fetch_command = "echo me"\n')

    result1 = ddev('config', 'allow')
    result2 = ddev('config', 'allow')

    assert result1.exit_code == 0, result1.output
    assert result2.exit_code == 0, result2.output


def test_allow_no_overrides_file_aborts(ddev):
    """Running `ddev config allow` without a .ddev.toml file exits with an error."""
    result = ddev('config', 'allow')

    assert result.exit_code != 0
