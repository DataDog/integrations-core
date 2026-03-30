import pytest

from ddev.config import secret_command
from ddev.config.secret_command import (
    SecretCommandError,
    _escape_unquoted_backslashes,
    parse_secret_command,
    reset_secret_command_cache,
    run_secret_command,
)
from ddev.config.secret_resolution import SecretResolutionError, resolve_optional_secret, resolve_required_secret


@pytest.fixture(autouse=True)
def reset_secret_command_cache_between_tests():
    reset_secret_command_cache()
    yield
    reset_secret_command_cache()


def test_error_code_command_parse(monkeypatch):
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', _raise_parse_error)

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
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', _raise_non_zero_error)

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


def test_optional_secret_executes_command_even_with_trust_block_flag(monkeypatch):
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', lambda _command: 'command-user')

    value = resolve_optional_secret(
        field_path='github.user',
        command='python user.py',
        literal='literal-user',
        env_var='DD_GITHUB_USER',
        env_value='env-user',
        command_blocked_by_trust=True,
    )

    assert value == 'command-user'


def test_optional_secret_trust_blocked_fallback_chain_without_command():
    assert (
        resolve_optional_secret(
            field_path='github.user',
            command=None,
            literal='literal-user',
            env_var='DD_GITHUB_USER',
            env_value='env-user',
            command_blocked_by_trust=True,
        )
        == 'literal-user'
    )

    assert (
        resolve_optional_secret(
            field_path='github.user',
            command=None,
            literal='   ',
            env_var='DD_GITHUB_USER',
            env_value='env-user',
            command_blocked_by_trust=True,
        )
        == 'env-user'
    )

    assert (
        resolve_optional_secret(
            field_path='github.user',
            command=None,
            literal='   ',
            env_var='DD_GITHUB_USER',
            env_value='',
            command_blocked_by_trust=True,
        )
        == ''
    )


def test_optional_secret_command_empty_output_hard_stop(monkeypatch):
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', lambda _command: '   ')

    with pytest.raises(SecretResolutionError) as e:
        resolve_optional_secret(
            field_path='github.user',
            command='python user.py',
            literal='literal-user',
            env_var='DD_GITHUB_USER',
            env_value='env-user',
        )

    assert e.value.code == 'secret-command-empty-output'


def test_optional_secret_command_executable_not_found(monkeypatch):
    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', _raise_executable_not_found_error)

    with pytest.raises(SecretResolutionError) as e:
        resolve_optional_secret(
            field_path='github.user',
            command='missing-executable-12345',
            literal='literal-user',
            env_var='DD_GITHUB_USER',
            env_value='env-user',
        )

    assert e.value.code == 'secret-command-executable-not-found'


def test_optional_secret_command_none_uses_environment():
    value = resolve_optional_secret(
        field_path='github.user',
        command=None,
        literal=None,
        env_var='DD_GITHUB_USER',
        env_value='env-user',
    )

    assert value == 'env-user'


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
        return type('P', (), {'returncode': 7, 'stdout': '', 'stderr': ''})()

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


def test_run_secret_command_non_zero_includes_stderr_summary(monkeypatch):
    def fake_run(*args, **kwargs):
        return type('P', (), {'returncode': 7, 'stdout': '', 'stderr': ' failed to fetch token '})()

    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

    with pytest.raises(SecretCommandError, match='exit code 7; stderr: failed to fetch token'):
        run_secret_command('python token.py')


def test_run_secret_command_executable_not_found_includes_executable_name(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError('simulated executable-not-found')

    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

    with pytest.raises(SecretCommandError, match=r"command executable was not found: 'missing-executable-12345'"):
        run_secret_command('missing-executable-12345 --arg')


def test_run_secret_command_start_error(monkeypatch):
    def fake_run(*args, **kwargs):
        raise OSError('simulated start failure')

    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

    with pytest.raises(SecretCommandError, match='command could not be started'):
        run_secret_command('python token.py')


def test_resolve_required_secret_maps_start_error(monkeypatch):
    monkeypatch.setattr('ddev.config.secret_command.subprocess.run', _raise_start_oserror)

    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command='python token.py',
            literal='literal-token',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'secret-command-start-error'


def test_resolve_required_secret_maps_empty_command_reason():
    with pytest.raises(SecretResolutionError) as e:
        resolve_required_secret(
            field_path='github.token',
            command='   ',
            literal='literal-token',
            env_var='GH_TOKEN',
        )

    assert e.value.code == 'secret-command-empty'


def test_parse_secret_command_uses_posix_mode(monkeypatch):
    captured = {}

    def fake_split(command, *, posix):
        captured['command'] = command
        captured['posix'] = posix
        return ['python', '-c', 'print(1)']

    for platform in ('linux', 'win32'):
        captured.clear()
        monkeypatch.setattr(secret_command.sys, 'platform', platform)
        monkeypatch.setattr(secret_command.shlex, 'split', fake_split)
        parse_secret_command('python -c "print(1)"')
        assert captured['posix'] is True, f'expected posix=True on {platform}'


def test_parse_secret_command_preserves_windows_backslashes(monkeypatch):
    monkeypatch.setattr(secret_command.sys, 'platform', 'win32')

    assert parse_secret_command(r'C:\Users\me\get-token.exe --flag') == [r'C:\Users\me\get-token.exe', '--flag']


def test_parse_secret_command_handles_single_quoted_windows_path(monkeypatch):
    # shlex.quote() wraps Windows paths in POSIX-style single quotes
    monkeypatch.setattr(secret_command.sys, 'platform', 'win32')

    result = parse_secret_command(r"'C:\Users\me\get-token.exe' --flag")
    assert result == [r'C:\Users\me\get-token.exe', '--flag']


def test_parse_secret_command_handles_double_quoted_windows_path_with_spaces(monkeypatch):
    # Paths with spaces must be double-quoted; POSIX mode handles this natively
    monkeypatch.setattr(secret_command.sys, 'platform', 'win32')

    result = parse_secret_command(r'"C:\Program Files\tool.exe" --flag')
    assert result == [r'C:\Program Files\tool.exe', '--flag']


# --- _escape_unquoted_backslashes unit tests ---


def test_escape_unquoted_backslashes_bare_path():
    assert _escape_unquoted_backslashes(r'C:\Users\me\tool.exe') == r'C:\\Users\\me\\tool.exe'


def test_escape_unquoted_backslashes_single_quoted_path_unchanged():
    cmd = r"'C:\Users\me\tool.exe'"
    assert _escape_unquoted_backslashes(cmd) == cmd


def test_escape_unquoted_backslashes_double_quoted_path_unchanged():
    cmd = r'"C:\Users\me\tool.exe"'
    assert _escape_unquoted_backslashes(cmd) == cmd


def test_escape_unquoted_backslashes_mixed():
    # bare path followed by double-quoted argument containing backslash
    cmd = r'C:\tool.exe "C:\data path\arg"'
    result = _escape_unquoted_backslashes(cmd)
    assert result == r'C:\\tool.exe "C:\data path\arg"'


def _parse_error():
    from ddev.config.secret_command import SecretCommandError

    return SecretCommandError('command could not be parsed', reason='parse_error')


def _non_zero_error():
    from ddev.config.secret_command import SecretCommandError

    return SecretCommandError('command failed with exit code 7', reason='non_zero_exit')


def _executable_not_found_error():
    from ddev.config.secret_command import SecretCommandError

    return SecretCommandError('command executable was not found', reason='executable_not_found')


def _raise_parse_error(_command):
    raise _parse_error()


def _raise_non_zero_error(_command):
    raise _non_zero_error()


def _raise_executable_not_found_error(_command):
    raise _executable_not_found_error()


def _raise_start_oserror(*args, **kwargs):
    raise OSError('simulated start failure')
