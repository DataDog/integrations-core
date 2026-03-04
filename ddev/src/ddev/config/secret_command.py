# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import shlex
import subprocess

DEFAULT_SECRET_COMMAND_TIMEOUT = 5
_SECRET_COMMAND_CACHE: dict[tuple[str, float], str] = {}


class SecretCommandError(Exception):
    def __init__(self, message: str, *, reason: str):
        self.reason = reason
        super().__init__(message)


def parse_secret_command(command: str) -> list[str]:
    try:
        argv = shlex.split(command, posix=os.name != 'nt')
    except ValueError as e:
        raise SecretCommandError('command could not be parsed', reason='parse_error') from e

    if not argv:
        raise SecretCommandError('command is empty', reason='empty_command')

    return argv


def run_secret_command(command: str, *, timeout: float | None = None) -> str:
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
        raise SecretCommandError(f'command failed with exit code {process.returncode}', reason='non_zero_exit')

    secret = process.stdout.strip()
    _SECRET_COMMAND_CACHE[cache_key] = secret
    return secret


def reset_secret_command_cache() -> None:
    _SECRET_COMMAND_CACHE.clear()
