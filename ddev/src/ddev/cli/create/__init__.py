# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
``ddev create`` command group.

This module is intentionally light at import time: only ``click`` and the
subcommand modules are imported up-front. Heavy helpers (template walker,
config-override writer, ``tomli_w``) load inside the command function
bodies so ``ddev create --help`` stays fast.
"""

from __future__ import annotations

import enum

import click

from ddev.cli.create.check import check
from ddev.cli.create.check_only import check_only
from ddev.cli.create.event import event
from ddev.cli.create.jmx import jmx
from ddev.cli.create.logs import logs
from ddev.cli.create.metrics_crawler import metrics_crawler

CONFLUENCE_NO_MANIFEST_URL = 'https://datadoghq.atlassian.net/wiki/spaces/AI/pages/6248108729/'

LEGACY_TYPE_TO_SUBCOMMAND: dict[str, str] = {
    'check': 'check',
    'check_only': 'check-only',
    'jmx': 'jmx',
    'logs': 'logs',
    'event': 'event',
    'metrics_crawler': 'metrics-crawler',
}

DROPPED_LEGACY_TYPES = {'tile', 'snmp_tile', 'marketplace'}


class _CreateGroup(click.Group):
    """Group that accepts ``ddev create NAME --type=...`` as a deprecation shim."""

    def resolve_command(  # type: ignore[override]
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        from ddev.cli.application import Application

        if not args:
            return super().resolve_command(ctx, args)

        first = args[0]
        if self.get_command(ctx, first) is not None:
            return super().resolve_command(ctx, args)

        app: Application = ctx.obj
        legacy_type = _extract_legacy_type(args)

        if legacy_type is _MISSING_TYPE_VALUE:
            app.abort('`--type` / `-t` requires a value (e.g. `--type=check`).')

        # No `--type`: the user passed a bare positional (the legacy `ddev create NAME` shape
        # that is now ambiguous). Point them at the new subcommand surface before click's
        # default "No such command" message lands.
        if legacy_type is None:
            app.abort(
                f'`ddev create {first}` is no longer supported. '
                f'Use a subcommand: `ddev create check {first}`, `ddev create logs {first}`, '
                f'etc. Run `ddev create --help` to see the full list.'
            )

        if legacy_type in DROPPED_LEGACY_TYPES:
            app.abort(
                f'`--type={legacy_type}` is no longer supported. '
                f'Use the manifest-less workflow described at {CONFLUENCE_NO_MANIFEST_URL}.'
            )

        # mypy doesn't propagate `app.abort`'s NoReturn through the typed `ctx.obj`
        # assignment, so narrow explicitly here.
        assert isinstance(legacy_type, str)
        target = LEGACY_TYPE_TO_SUBCOMMAND.get(legacy_type)
        if target is None:
            app.abort(f'Unknown integration type: `{legacy_type}`.')

        subcommand = self.get_command(ctx, target)
        if subcommand is None:
            app.abort(f'Internal error: subcommand `{target}` not registered.')
        assert subcommand is not None  # for the type checker; abort above is NoReturn

        app.display_warning(
            f'`--type={legacy_type}` is deprecated. '
            f'Use `ddev create {target} NAME` instead. The flag will be removed in a future release.'
        )

        cleaned = _strip_type_flag(args)
        return subcommand.name, subcommand, cleaned


class _TypeFlagSentinel(enum.Enum):
    """Nominal sentinel type so mypy can narrow ``_extract_legacy_type``'s return value."""

    MISSING = 'missing'


# Sentinel: ``--type`` / ``-t`` was passed but no value followed (e.g. trailing ``--type``).
_MISSING_TYPE_VALUE: _TypeFlagSentinel = _TypeFlagSentinel.MISSING

# Recognised spellings of the deprecated ``--type`` / ``-t`` flag.
# Used by both ``_extract_legacy_type`` and ``_strip_type_flag``; update once if a
# new spelling is ever added.
_TYPE_FLAG_LITERALS: tuple[str, ...] = ('--type', '-t')
_TYPE_FLAG_EQUALS_PREFIXES: tuple[str, ...] = ('--type=', '-t=')


def _extract_legacy_type(args: list[str]) -> str | _TypeFlagSentinel | None:
    """Return the `--type` / `-t` value from ``args``.

    Distinguishes three outcomes:
      - ``None``: no `--type` / `-t` flag present at all.
      - ``_MISSING_TYPE_VALUE``: the flag is present but has no following value.
      - ``str``: the flag is present with a value.
    """
    iterator = iter(args)
    for token in iterator:
        if token in _TYPE_FLAG_LITERALS:
            value = next(iterator, _MISSING_TYPE_VALUE)
            # If the next token is itself a flag (e.g. `--type --dry-run`), treat the
            # value as missing — the user clearly didn't intend to pass `--dry-run`
            # as the type name.
            if isinstance(value, str) and value.startswith('-'):
                return _MISSING_TYPE_VALUE
            return value
        for prefix in _TYPE_FLAG_EQUALS_PREFIXES:
            if token.startswith(prefix):
                value = token[len(prefix) :]
                # `--type=` with nothing after the equals sign is a missing value, not the
                # empty-string type name `''` (which would abort with a confusing message).
                return value if value else _MISSING_TYPE_VALUE
        if _is_concatenated_short_type(token):
            return token[2:]
    return None


def _is_concatenated_short_type(token: str) -> bool:
    """Match the legacy ``-tcheck`` short-flag form without swallowing future ``-tXxx`` options."""
    if not token.startswith('-t') or len(token) <= 2 or token.startswith('--'):
        return False
    candidate = token[2:]
    return candidate in LEGACY_TYPE_TO_SUBCOMMAND or candidate in DROPPED_LEGACY_TYPES


def _strip_type_flag(args: list[str]) -> list[str]:
    """Remove the legacy ``--type`` / ``-t`` flag from ``args`` (allow-listed forms only)."""
    cleaned: list[str] = []
    skip_next = False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if token in _TYPE_FLAG_LITERALS:
            skip_next = True
            continue
        if token.startswith(_TYPE_FLAG_EQUALS_PREFIXES):
            continue
        if _is_concatenated_short_type(token):
            continue
        cleaned.append(token)
    return cleaned


@click.group(
    cls=_CreateGroup,
    short_help='Scaffold a new integration',
    # ignore_unknown_options lets the legacy `--type` / `-t` flag survive the group's
    # option parser when it appears before the positional name (e.g. the previously
    # documented `ddev create --type jmx NAME`). Without it, click rejects `--type`
    # with "No such option" before resolve_command's deprecation shim ever runs.
    context_settings={'help_option_names': ['-h', '--help'], 'ignore_unknown_options': True},
)
def create() -> None:
    """Scaffold a new integration.

    Use one of the subcommands (``check``, ``check-only``, ``jmx``, ``logs``,
    ``event``, ``metrics-crawler``).

    The ``--type`` / ``-t`` flag from the legacy CLI is accepted as a
    deprecation shim and will be removed in a future release.
    """


create.add_command(check)
create.add_command(check_only)
create.add_command(jmx)
create.add_command(logs)
create.add_command(event)
create.add_command(metrics_crawler)
