"""Tests for build_wheels.assert_kafka_version_matches."""

import pytest

import build_wheels


@pytest.fixture
def write_requirements(tmp_path, monkeypatch):
    """Point build_wheels.MOUNT_DIR at a tmp dir; return a helper that writes requirements.in."""
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)

    def _write(pin_line: str) -> None:
        (tmp_path / 'requirements.in').write_text(f'{pin_line}\n', encoding='utf-8')

    return _write


@pytest.mark.parametrize(
    'pin_line, env_version, should_abort',
    [
        ('confluent-kafka==2.13.2', '2.13.1', True),     # drift
        ('confluent-kafka==2.13.2', '2.13.2', False),    # match
        ('# no kafka pin here',     '2.13.2', True),     # env set but no pin in file
    ],
    ids=['drift', 'match', 'no-pin'],
)
def test_with_env_set(write_requirements, monkeypatch, pin_line, env_version, should_abort):
    write_requirements(pin_line)
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', env_version)

    if should_abort:
        with pytest.raises(SystemExit):
            build_wheels.assert_kafka_version_matches()
    else:
        build_wheels.assert_kafka_version_matches()


def test_noop_when_env_unset(write_requirements, monkeypatch):
    write_requirements('confluent-kafka==2.13.2')
    monkeypatch.delenv('CONFLUENT_KAFKA_VERSION', raising=False)

    build_wheels.assert_kafka_version_matches()


def test_aborts_when_requirements_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()
