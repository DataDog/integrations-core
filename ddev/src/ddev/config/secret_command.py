# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import shlex
import subprocess
import sys

DEFAULT_SECRET_COMMAND_TIMEOUT = 5
_SECRET_COMMAND_CACHE: dict[tuple[str, float], str] = {}


class SecretCommandError(Exception):
    def __init__(self, message: str, *, reason: str):
        self.reason = reason
        super().__init__(message)


def parse_secret_command(command: str) -> list[str]:
    """Parse a command string into argv.

    On Windows, bare backslash paths (e.g. ``C:\\path\\tool.exe``) are
    supported without quoting, and both single-quoted and double-quoted paths
    work too.  The implementation pre-escapes unquoted backslashes so that
    POSIX shlex can be used uniformly on all platforms.
    """
    if sys.platform == 'win32':
        command = _escape_unquoted_backslashes(command)
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as e:
        raise SecretCommandError('command could not be parsed', reason='parse_error') from e

    if not argv:
        raise SecretCommandError('command is empty', reason='empty_command')

    return argv


def _escape_unquoted_backslashes(command: str) -> str:
    """Double backslashes that appear outside quoted regions.

    POSIX shlex treats a bare ``\\`` as an escape character, eating the
    following character.  Doubling unquoted backslashes before POSIX parsing
    ensures they survive as literal path separators.  Backslashes inside
    single or double quotes are left untouched: POSIX shlex already handles
    them correctly there (all chars literal inside single quotes; only special
    chars escaped inside double quotes).
    """
    result = []
    in_single = False
    in_double = False
    for ch in command:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == '\\' and not in_single and not in_double:
            result.append('\\')  # prepend extra backslash so POSIX sees \\→\
        result.append(ch)
    return ''.join(result)


def run_secret_command(command: str, *, timeout: float | None = None) -> str:
    """Run a secret provider command and cache successful stdout by command+timeout."""
    timeout = DEFAULT_SECRET_COMMAND_TIMEOUT if timeout is None else timeout
    cache_key = (command, timeout)
    if cache_key in _SECRET_COMMAND_CACHE:
        return _SECRET_COMMAND_CACHE[cache_key]

    argv = parse_secret_command(command)

    try:
        process = subprocess.run(
            argv,
            check=False,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise SecretCommandError('command executable was not found', reason='executable_not_found') from e
    except subprocess.TimeoutExpired as e:
        raise SecretCommandError(f'command timed out after {timeout:g}s', reason='timeout') from e
    except OSError as e:
        raise SecretCommandError('command could not be started', reason='start_error') from e

    if process.returncode != 0:
        stderr_summary = _summarize_stderr(getattr(process, 'stderr', ''))
        stderr_suffix = f'; stderr: {stderr_summary}' if stderr_summary else ''
        raise SecretCommandError(
            f'command failed with exit code {process.returncode}{stderr_suffix}', reason='non_zero_exit'
        )

    secret = process.stdout.strip()
    _SECRET_COMMAND_CACHE[cache_key] = secret
    return secret


def reset_secret_command_cache() -> None:
    _SECRET_COMMAND_CACHE.clear()


def _summarize_stderr(stderr: str) -> str:
    collapsed = ' '.join(stderr.split())
    if not collapsed:
        return ''

    max_length = 200
    if len(collapsed) > max_length:
        return f'{collapsed[: max_length - 3]}...'
    return collapsed
