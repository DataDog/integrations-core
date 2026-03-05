# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from ddev.config.trust import (
    deny_local_config,
    is_local_config_trusted,
    load_trust_records,
    trust_local_config,
)
from ddev.utils.fs import Path


def test_trust_local_config_records_hash(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'
    local_config.write_text('[github]\ntoken_command = "python token.py"\n')

    already_trusted = trust_local_config(local_config)
    trust_records = load_trust_records()
    record = trust_records[str(local_config.expand().resolve())]

    assert already_trusted is False
    assert record.path == str(local_config.expand().resolve())
    assert record.sha256


def test_trust_local_config_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'
    local_config.write_text('[github]\ntoken_command = "python token.py"\n')

    trust_local_config(local_config)
    already_trusted = trust_local_config(local_config)

    assert already_trusted is True


def test_deny_local_config_removes_record(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'
    local_config.write_text('[github]\ntoken_command = "python token.py"\n')
    trust_local_config(local_config)

    removed = deny_local_config(local_config)

    assert removed is True
    assert load_trust_records() == {}


def test_deny_local_config_when_absent(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'

    removed = deny_local_config(local_config)

    assert removed is False


def test_is_local_config_trusted_false_when_file_changes(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'
    local_config.write_text('[github]\ntoken_command = "python token.py"\n')
    trust_local_config(local_config)

    local_config.write_text('[github]\ntoken_command = "python changed-token.py"\n')

    assert is_local_config_trusted(local_config) is False


def test_is_local_config_trusted_false_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'

    assert is_local_config_trusted(local_config) is False


def test_trust_local_config_does_not_write_when_already_trusted(monkeypatch, tmp_path, mocker):
    monkeypatch.setenv('DDEV_DATA_DIR', str(tmp_path / 'ddev-data'))
    local_config = Path(tmp_path) / '.ddev.toml'
    local_config.write_text('[github]\ntoken_command = "python token.py"\n')
    trust_local_config(local_config)  # first call — writes

    save_mock = mocker.patch('ddev.config.trust.save_trust_records')
    trust_local_config(local_config)  # second call — should skip write

    save_mock.assert_not_called()


def test_load_trust_records_returns_empty_for_invalid_toml(tmp_path):
    trust_store_path = Path(tmp_path) / 'trusted-local-configs.toml'
    trust_store_path.write_text('records = [\n')

    assert load_trust_records(trust_store_path) == {}
