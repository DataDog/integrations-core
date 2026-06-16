"""Tests for build_wheels.assert_kafka_version_matches."""

import re

import pytest

import build_wheels


@pytest.fixture
def mount_dir(tmp_path, monkeypatch):
    """Point build_wheels.MOUNT_DIR at a tmp dir and return the path."""
    monkeypatch.setattr(build_wheels, 'MOUNT_DIR', tmp_path)
    return tmp_path


@pytest.fixture
def write_requirements(mount_dir):
    """Write requirements.in lines into the mounted dir."""
    def _write(*pin_lines: str) -> None:
        (mount_dir / 'requirements.in').write_text('\n'.join(pin_lines) + '\n', encoding='utf-8')

    return _write


def _assert_aborts_with(capsys, pattern: str) -> None:
    """Assert that the most recent SystemExit printed a stderr message matching the given regex."""
    err = capsys.readouterr().err
    assert re.search(pattern, err), f'expected stderr to match {pattern!r}; got: {err!r}'


@pytest.mark.parametrize(
    'pin_line, env_version, abort_pattern',
    [
        ('confluent-kafka==2.13.2',                            '2.13.1', 'disagrees'),
        ('confluent-kafka==2.13.2',                            '2.13.2', None),
        ('# no kafka pin here',                                '2.13.2', 'no .*== pin'),
        ('confluent-kafka==2.13.2; sys_platform != "darwin"',  '2.13.2', None),
        ('confluent-kafka==2.13.2  # pin',                     '2.13.2', None),
        ('confluent-kafka[avro]==2.13.2',                      '2.13.2', None),
        ('  confluent-kafka==2.13.2  ',                        '2.13.2', None),
        ('confluent-kafka>=2.13.2',                            '2.13.2', 'no .*== pin'),
    ],
    ids=['drift', 'match', 'no-pin', 'env-marker', 'inline-comment', 'extras', 'surrounding-ws', 'non-eq-operator'],
)
def test_with_env_set(write_requirements, monkeypatch, capsys, pin_line, env_version, abort_pattern):
    write_requirements(pin_line)
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', env_version)

    if abort_pattern is None:
        build_wheels.assert_kafka_version_matches()
    else:
        with pytest.raises(SystemExit):
            build_wheels.assert_kafka_version_matches()
        _assert_aborts_with(capsys, abort_pattern)


def test_noop_when_env_unset(mount_dir, monkeypatch):
    # MOUNT_DIR points at an empty dir — no requirements.in present
    monkeypatch.delenv('CONFLUENT_KAFKA_VERSION', raising=False)
    build_wheels.assert_kafka_version_matches()


def test_marker_aware_pin_selection_uses_windows_pin(write_requirements, monkeypatch):
    write_requirements(
        'confluent-kafka==2.13.1; sys_platform == "darwin"',
        'confluent-kafka==2.13.2; sys_platform == "win32"',
    )
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')

    build_wheels.assert_kafka_version_matches()


def test_marker_aware_pin_selection_aborts_on_windows_pin_drift(write_requirements, monkeypatch, capsys):
    write_requirements(
        'confluent-kafka==2.13.1; sys_platform == "darwin"',
        'confluent-kafka==2.13.2; sys_platform == "win32"',
    )
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.3')

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()
    _assert_aborts_with(capsys, 'disagrees.*2\\.13\\.2')


def test_aborts_on_multiple_applicable_windows_pins(write_requirements, monkeypatch, capsys):
    write_requirements(
        'confluent-kafka==2.13.1',
        'confluent-kafka==2.13.2; sys_platform == "win32"',
    )
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()
    _assert_aborts_with(capsys, 'multiple Windows confluent-kafka pins')


def test_aborts_when_requirements_file_missing(mount_dir, monkeypatch, capsys):
    monkeypatch.setenv('CONFLUENT_KAFKA_VERSION', '2.13.2')

    with pytest.raises(SystemExit):
        build_wheels.assert_kafka_version_matches()
    _assert_aborts_with(capsys, 'is missing')
