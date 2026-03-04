import pytest

from ddev.config.secret_command import reset_secret_command_cache
from ddev.config.secret_resolution import SecretResolutionError, resolve_required_secret


@pytest.fixture(autouse=True)
def reset_secret_command_cache_between_tests():
    reset_secret_command_cache()
    yield
    reset_secret_command_cache()


def test_error_code_command_parse(monkeypatch):
    monkeypatch.setattr(
        'ddev.config.secret_resolution.run_secret_command', lambda _command: (_ for _ in ()).throw(_parse_error())
    )

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command='bad command',
            literal='literal-token',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'secret-command-parse-error'
    assert e.value.field_path == 'github.token'
    assert e.value.source_summary.command == 'configured'
    assert e.value.source_summary.literal == 'present'
    assert e.value.source_summary.environment == 'GH_TOKEN:absent'
    assert 'syntax and quoting' in e.value.remediation_hint


def test_error_code_missing_required_secret(monkeypatch):
    monkeypatch.delenv('GH_TOKEN', raising=False)

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command=None,
            literal='   ',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'missing-required-secret'
    assert e.value.source_summary.command == 'absent'
    assert e.value.source_summary.literal == 'blank'
    assert e.value.source_summary.environment == 'GH_TOKEN:absent'
    assert 'Set *_command' in e.value.remediation_hint


def test_precedence_command_beats_literal_and_env(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', lambda _command: 'command-token')

    value = resolve_required_secret(
        field_path='github.token',
        command='python token.py',
        literal='literal-token',
        env_var='GH_TOKEN',
    )

    assert value == 'command-token'


def test_precedence_literal_beats_env_when_command_absent(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')

    value = resolve_required_secret(
        field_path='github.token',
        command=None,
        literal='literal-token',
        env_var='GH_TOKEN',
    )

    assert value == 'literal-token'


def test_precedence_env_fallback_when_command_and_literal_absent(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')

    value = resolve_required_secret(
        field_path='github.token',
        command=None,
        literal=None,
        env_var='GH_TOKEN',
    )

    assert value == 'env-token'


def test_precedence_command_empty_output_hard_stop(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', lambda _command: '   ')

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command='python token.py',
            literal='literal-token',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'secret-command-empty-output'


def test_precedence_command_failure_hard_stop(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')
    monkeypatch.setattr(
        'ddev.config.secret_resolution.run_secret_command', lambda _command: (_ for _ in ()).throw(_non_zero_error())
    )

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command='python token.py',
            literal='literal-token',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'secret-command-non-zero-exit'


def test_precedence_blank_literal_treated_as_absent(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'env-token')

    value = resolve_required_secret(
        field_path='github.token',
        command=None,
        literal='   ',
        env_var='GH_TOKEN',
    )

    assert value == 'env-token'


def test_precedence_missing_required_secret_summary_shape(monkeypatch):
    monkeypatch.delenv('GH_TOKEN', raising=False)

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command=None,
            literal=None,
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'missing-required-secret'
    assert e.value.field_path == 'github.token'
    assert e.value.source_summary.command == 'absent'
    assert e.value.source_summary.literal == 'absent'
    assert e.value.source_summary.environment == 'GH_TOKEN:absent'


def test_identical_command_executes_once_per_process(monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return type('P', (), {'returncode': 0, 'stdout': 'from-command'})()

    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

    first = resolve_required_secret(
        field_path='github.token',
        command='python token.py',
        literal=None,
        env_var='GH_TOKEN',
    )
    second = resolve_required_secret(
        field_path='github.token',
        command='python token.py',
        literal=None,
        env_var='GH_TOKEN',
    )

    assert first == 'from-command'
    assert second == 'from-command'
    assert len(calls) == 1


def test_failed_command_is_not_cached(monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return type('P', (), {'returncode': 7, 'stdout': ''})()

    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

    with pytest.raises(SecretResolutionError):
        resolve_required_secret(
            field_path='github.token',
            command='python token.py',
            literal=None,
            env_var='GH_TOKEN',
        )

    with pytest.raises(SecretResolutionError):
        resolve_required_secret(
            field_path='github.token',
            command='python token.py',
            literal=None,
            env_var='GH_TOKEN',
        )

    assert len(calls) == 2


def _parse_error():
    from ddev.config.secret_command import SecretCommandError

    return SecretCommandError('command could not be parsed', reason='parse_error')


def _non_zero_error():
    from ddev.config.secret_command import SecretCommandError

    return SecretCommandError('command failed with exit code 7', reason='non_zero_exit')
