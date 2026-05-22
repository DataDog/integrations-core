"""Tests for build_wheels.assert_kafka_version_matches."""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import build_wheels  # noqa: E402


def _write_requirements(mount_dir: Path, pin_line: str) -> None:
    (mount_dir / 'requirements.in').write_text(f'{pin_line}\n', encoding='utf-8')


def test_drift_aborts_when_env_disagrees(tmp_path, monkeypatch):
    _write_requirements(tmp_path, 'confluent-kafka==2.13.2')
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.1')
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()


def test_drift_passes_when_env_matches(tmp_path, monkeypatch):
    _write_requirements(tmp_path, 'confluent-kafka==2.13.2')
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)

    build_wheels.assert_kafka_version_matches()


def test_noop_when_env_unset(tmp_path, monkeypatch):
    _write_requirements(tmp_path, 'confluent-kafka==2.13.2')
    monkeypatch.delenv('CONFLUENT_KAFKA_VERSION', raising=False)
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)

    build_wheels.assert_kafka_version_matches()


def test_aborts_when_env_set_but_no_pin(tmp_path, monkeypatch):
    _write_requirements(tmp_path, '# no kafka pin here')
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()
