# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-process command resolver with deterministic caching for `*_fetch_command` secret fields."""
from __future__ import annotations

import subprocess

# Failure reasons surfaced by CommandExecutionError.
NON_ZERO_EXIT = 'non_zero_exit'
EMPTY_OUTPUT = 'empty_output'

# Per-process cache keyed by exact command string.
_COMMAND_CACHE: dict[str, str] = {}


class CommandExecutionError(Exception):
    """Raised when a secret-resolution command exits non-zero or produces no output."""

    _MAX_STDERR_CHARS = 200

    def __init__(self, command: str, returncode: int, stderr: str, reason: str):
        self.command = command
        self.returncode = returncode
        self.reason = reason
        self.stderr = stderr.strip()
        super().__init__(self._reason_message())

    def _stderr_excerpt(self) -> str:
        if not self.stderr:
            return ''

        # Keep user-facing output compact and single-line.
        cleaned = ' '.join(self.stderr.split())
        if len(cleaned) > self._MAX_STDERR_CHARS:
            return f'{cleaned[: self._MAX_STDERR_CHARS - 3]}...'
        return cleaned

    def _reason_message(self) -> str:
        if self.reason == EMPTY_OUTPUT:
            return 'command returned empty output'

        stderr_excerpt = self._stderr_excerpt()
        if stderr_excerpt:
            return f'command failed with exit code {self.returncode}: {stderr_excerpt}'
        return f'command failed with exit code {self.returncode}'

    def to_user_message(self, field_path: str) -> str:
        return (
            f"Failed to resolve `{field_path}`: {self._reason_message()}. "
            "Check that the configured *_fetch_command exists, is executable, writes the secret to stdout, "
            "and returns a non-empty value."
        )


def run_command(command: str) -> str:
    """Execute *command* in a shell and return stdout stripped of surrounding whitespace.

    Results are cached per-process so each distinct command string runs at most once.

    Raises:
        TypeError: if *command* is not a ``str``.
        CommandExecutionError: if the command exits with a non-zero return code or
            produces empty output after stripping.
    """
    if not isinstance(command, str):
        raise TypeError(f'command must be a str, got {type(command).__name__!r}')

    if command in _COMMAND_CACHE:
        return _COMMAND_CACHE[command]

    result = subprocess.run(command, shell=True, text=True, capture_output=True, check=False)

    if result.returncode != 0:
        raise CommandExecutionError(command, result.returncode, result.stderr, reason=NON_ZERO_EXIT)

    value = result.stdout.strip()
    if not value:
        raise CommandExecutionError(command, result.returncode, result.stderr, reason=EMPTY_OUTPUT)

    _COMMAND_CACHE[command] = value
    return value


def clear_cache() -> None:
    """Clear the per-process command cache.  Intended for use in tests only."""
    _COMMAND_CACHE.clear()
