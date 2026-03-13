# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from ddev.config.file import ConfigFileWithOverrides
from ddev.config.trust import deny_local_config, is_local_config_trusted, trust_local_config
from ddev.utils.fs import Path


def test_allow_trusts_local_config(ddev, monkeypatch, tmp_path, helpers, overrides_config: Path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token_command = "python token.py"
            """
        )
    )

    result = ddev('config', 'allow')

    assert result.exit_code == 0, result.output
    assert 'Trusted local config:' in result.output
    assert 'Trust is bound to this file hash' in result.output
    assert is_local_config_trusted(overrides_config)


def test_allow_is_idempotent(ddev, monkeypatch, tmp_path, helpers, overrides_config: Path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token = "abc123"
            """
        )
    )
    trust_local_config(overrides_config)

    result = ddev('config', 'allow')

    assert result.exit_code == 0, result.output
    assert 'Local config is already trusted:' in result.output


def test_allow_without_local_file(ddev, monkeypatch, tmp_path, temp_dir: Path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))

    with temp_dir.as_cwd():
        result = ddev('config', 'allow')

    assert result.exit_code == 0, result.output
    assert 'No local config file found' in result.output


def test_deny_removes_trust(ddev, monkeypatch, tmp_path, helpers, overrides_config: Path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token = "abc123"
            """
        )
    )
    trust_local_config(overrides_config)

    result = ddev('config', 'deny')

    assert result.exit_code == 0, result.output
    assert 'Removed trust for local config:' in result.output
    assert not is_local_config_trusted(overrides_config)


def test_deny_is_idempotent(ddev, monkeypatch, tmp_path, helpers, overrides_config: Path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token_command = "python token.py"
            """
        )
    )

    result = ddev('config', 'deny')

    assert result.exit_code == 0, result.output
    assert 'Local config is already untrusted:' in result.output


def test_trust_lifecycle_untrusted_allow_edit_revokes_and_deny(
    ddev, monkeypatch, tmp_path, helpers, overrides_config: Path, config_file: ConfigFileWithOverrides
):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token_command = "python token.py"
            """
        )
    )

    config_file.load()
    assert 'token_command' not in config_file.overrides_model.raw_data['github']

    allow_result = ddev('config', 'allow')
    assert allow_result.exit_code == 0, allow_result.output

    config_file.load()
    assert config_file.overrides_model.raw_data['github']['token_command'] == 'python token.py'

    overrides_config.write_text(
        helpers.dedent(
            """
            [github]
            token_command = "python new-token.py"
            """
        )
    )
    assert not is_local_config_trusted(overrides_config)

    deny_result = ddev('config', 'deny')
    assert deny_result.exit_code == 0, deny_result.output

    assert not deny_local_config(overrides_config)
