# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest

from ddev.config.command_resolver import (
    EMPTY_OUTPUT,
    NON_ZERO_EXIT,
    CommandExecutionError,
    clear_cache,
    run_command,
)


@pytest.fixture(autouse=True)
def fresh_cache():
    """Ensure a clean cache before and after every test."""
    clear_cache()
    yield
    clear_cache()


class TestRunCommand:
    def test_returns_stdout_stripped(self):
        result = run_command('echo hello')
        assert result == 'hello'

    def test_caches_result(self, mocker):
        spy = mocker.patch('subprocess.run', wraps=__import__('subprocess').run)
        run_command('echo cached')
        run_command('echo cached')
        assert spy.call_count == 1

    def test_distinct_commands_each_run_once(self, mocker):
        spy = mocker.patch('subprocess.run', wraps=__import__('subprocess').run)
        run_command('echo first')
        run_command('echo second')
        assert spy.call_count == 2

    def test_nonzero_exit_raises(self):
        with pytest.raises(CommandExecutionError) as exc_info:
            run_command('exit 42')
        assert exc_info.value.returncode == 42
        assert exc_info.value.reason == NON_ZERO_EXIT
        assert 'exit code 42' in str(exc_info.value)

    def test_empty_output_raises(self):
        with pytest.raises(CommandExecutionError) as exc_info:
            run_command(f'{sys.executable} -c "pass"')
        assert exc_info.value.reason == EMPTY_OUTPUT
        assert 'empty output' in str(exc_info.value)

    def test_type_error_on_non_string(self):
        with pytest.raises(TypeError):
            run_command(123)  # type: ignore[arg-type]

    def test_error_is_secret_safe(self):
        with pytest.raises(CommandExecutionError) as exc_info:
            run_command('echo super-secret && exit 1')
        assert 'super-secret' not in str(exc_info.value)

    def test_actionable_message_mentions_field_and_hints(self):
        with pytest.raises(CommandExecutionError) as exc_info:
            run_command('exit 1')

        user_message = exc_info.value.to_user_message('github.token_fetch_command')
        assert 'github.token_fetch_command' in user_message
        assert 'stdout' in user_message
        assert 'non-empty value' in user_message


class TestClearCache:
    def test_clear_forces_re_execution(self, mocker):
        spy = mocker.patch('subprocess.run', wraps=__import__('subprocess').run)
        run_command('echo test')
        clear_cache()
        run_command('echo test')
        assert spy.call_count == 2
