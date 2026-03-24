# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.config.file import ConfigFileWithOverrides
from ddev.config.trust import TrustStorePersistenceError, deny_local_config, is_local_config_trusted, trust_local_config
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


@pytest.mark.parametrize(
    ('command', 'patch_target'),
    [
        ('allow', 'ddev.cli.config.allow.trust_local_config'),
        ('deny', 'ddev.cli.config.deny.deny_local_config'),
    ],
)
def test_allow_deny_surfaces_trust_store_write_failures(
    ddev, monkeypatch, tmp_path, overrides_config: Path, mocker, command: str, patch_target: str
) -> None:
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    mocker.patch(
        patch_target,
        side_effect=TrustStorePersistenceError(
            'Unable to update the trust store at `/tmp/trusted-local-configs.toml`. '
            'Check that this path is writable and try again.'
        ),
    )

    result = ddev('config', command)

    assert result.exit_code == 1, result.output
    assert 'Unable to update the trust store at `/tmp/trusted-local-configs.toml`.' in result.output
    assert 'Check that this path is writable and try again.' in result.output
    assert 'Traceback' not in result.output
