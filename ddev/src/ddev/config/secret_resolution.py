"""Deterministic secret source resolution contract."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ddev.config.secret_command import SecretCommandError, run_secret_command


@dataclass(frozen=True)
class SecretSourceSummary:
    command: str
    literal: str
    environment: str


class SecretResolutionError(Exception):
    def __init__(
        self,
        *,
        code: str,
        field_path: str,
        source_summary: SecretSourceSummary,
        remediation_hint: str,
    ):
        self.code = code
        self.field_path = field_path
        self.source_summary = source_summary
        self.remediation_hint = remediation_hint

        message = (
            f'[{code}] could not resolve required secret for {field_path}; '
            f'sources(command={source_summary.command}, '
            f'literal={source_summary.literal}, env={source_summary.environment}); '
            f'{remediation_hint}'
        )
        super().__init__(message)


_COMMAND_REASON_TO_CODE = {
    'parse_error': 'secret-command-parse-error',
    'empty_command': 'secret-command-empty',
    'executable_not_found': 'secret-command-executable-not-found',
    'timeout': 'secret-command-timeout',
    'start_error': 'secret-command-start-error',
    'non_zero_exit': 'secret-command-non-zero-exit',
}

_COMMAND_REASON_TO_HINT = {
    'parse_error': 'Check the configured *_command syntax and quoting.',
    'empty_command': 'Set a non-empty *_command value or remove it to use fallback sources.',
    'executable_not_found': 'Install the command executable or fix the configured *_command path.',
    'timeout': 'Ensure the command completes within the timeout or optimize the provider command.',
    'start_error': 'Check command permissions and executable startup requirements.',
    'non_zero_exit': 'Run the configured *_command directly and fix its failing exit code.',
}


def _source_summary(
    command: str | None,
    literal: str | None,
    env_label: str,
    env_value: str,
    *,
    command_blocked_by_trust: bool,
) -> SecretSourceSummary:
    literal_state = 'absent'
    if literal is not None:
        literal_state = 'present' if not _is_blank_secret(literal) else 'blank'

    return SecretSourceSummary(
        command='blocked-untrusted-local-config'
        if command_blocked_by_trust
        else ('configured' if command is not None else 'absent'),
        literal=literal_state,
        environment=f'{env_label}:present' if env_value else f'{env_label}:absent',
    )


def resolve_required_secret(
    *,
    field_path: str,
    command: str | None,
    literal: str | None,
    env_var: str,
    env_value: str | None = None,
    env_label: str | None = None,
    command_blocked_by_trust: bool = False,
) -> str:
    """Resolve a required secret with deterministic precedence.

    Order: command -> literal -> env -> hard failure.
    """
    resolved_env_label = env_label or env_var
    resolved_env_value = env_value if env_value is not None else os.environ.get(env_var, '')

    if command is not None:
        try:
            command_value = run_secret_command(command)
        except SecretCommandError as e:
            summary = _source_summary(
                command,
                literal,
                resolved_env_label,
                resolved_env_value,
                command_blocked_by_trust=command_blocked_by_trust,
            )
            code = _COMMAND_REASON_TO_CODE.get(e.reason, 'secret-command-error')
            hint = _COMMAND_REASON_TO_HINT.get(e.reason, 'Check the configured *_command value and try again.')
            raise SecretResolutionError(
                code=code,
                field_path=field_path,
                source_summary=summary,
                remediation_hint=hint,
            ) from e

        if not command_value.strip():
            summary = _source_summary(
                command,
                literal,
                resolved_env_label,
                resolved_env_value,
                command_blocked_by_trust=command_blocked_by_trust,
            )
            raise SecretResolutionError(
                code='secret-command-empty-output',
                field_path=field_path,
                source_summary=summary,
                remediation_hint='Ensure the configured *_command prints a non-empty secret value.',
            )

        return command_value

    if literal is not None and not _is_blank_secret(literal):
        return literal

    if resolved_env_value:
        return resolved_env_value

    summary = _source_summary(
        command,
        literal,
        resolved_env_label,
        resolved_env_value,
        command_blocked_by_trust=command_blocked_by_trust,
    )
    remediation_hint = 'Set *_command, configure a literal secret, or export the expected environment variable.'
    if command_blocked_by_trust:
        remediation_hint = (
            f'{remediation_hint} The local *_command source was blocked because the local config is untrusted; '
            'run `ddev config allow` to trust the current file content or `ddev config deny` to clear trust records.'
        )
    raise SecretResolutionError(
        code='missing-required-secret',
        field_path=field_path,
        source_summary=summary,
        remediation_hint=remediation_hint,
    )


def resolve_optional_secret(
    *,
    field_path: str,
    command: str | None,
    literal: str | None,
    env_var: str,
    env_value: str | None = None,
    env_label: str | None = None,
    command_blocked_by_trust: bool = False,
) -> str:
    """Resolve an optional secret with deterministic precedence.

    Order: command -> literal -> env -> empty string.
    """
    resolved_env_label = env_label or env_var
    resolved_env_value = env_value if env_value is not None else os.environ.get(env_var, '')

    if command is not None and not command_blocked_by_trust:
        try:
            command_value = run_secret_command(command)
        except SecretCommandError as e:
            summary = _source_summary(
                command,
                literal,
                resolved_env_label,
                resolved_env_value,
                command_blocked_by_trust=command_blocked_by_trust,
            )
            code = _COMMAND_REASON_TO_CODE.get(e.reason, 'secret-command-error')
            hint = _COMMAND_REASON_TO_HINT.get(e.reason, 'Check the configured *_command value and try again.')
            raise SecretResolutionError(
                code=code,
                field_path=field_path,
                source_summary=summary,
                remediation_hint=hint,
            ) from e

        if not command_value.strip():
            summary = _source_summary(
                command,
                literal,
                resolved_env_label,
                resolved_env_value,
                command_blocked_by_trust=command_blocked_by_trust,
            )
            raise SecretResolutionError(
                code='secret-command-empty-output',
                field_path=field_path,
                source_summary=summary,
                remediation_hint='Ensure the configured *_command prints a non-empty secret value.',
            )

        return command_value

    if literal is not None and not _is_blank_secret(literal):
        return literal

    if resolved_env_value:
        return resolved_env_value

    return ''


def _is_blank_secret(value: str) -> bool:
    return not value.strip()
