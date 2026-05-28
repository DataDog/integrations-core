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
        if not args:
            return super().resolve_command(ctx, args)

        first = args[0]
        # If the first token matches a registered subcommand, use the normal flow.
        if self.get_command(ctx, first) is not None:
            return super().resolve_command(ctx, args)

        # If the user passes `--type=X` as a flag among `args`, we're in legacy mode.
        legacy_type = _extract_legacy_type(args)
        if legacy_type is None:
            return super().resolve_command(ctx, args)

        if legacy_type in DROPPED_LEGACY_TYPES:
            from ddev.cli.application import Application

            app: Application = ctx.obj
            app.abort(
                f'`--type={legacy_type}` is no longer supported. '
                f'Use the manifest-less workflow described at {CONFLUENCE_NO_MANIFEST_URL}.'
            )

        target = LEGACY_TYPE_TO_SUBCOMMAND.get(legacy_type)
        if target is None:
            ctx.fail(f'Unknown integration type: `{legacy_type}`.')

        subcommand = self.get_command(ctx, target)
        if subcommand is None:
            ctx.fail(f'Internal error: subcommand `{target}` not registered.')

        click.echo(
            f'WARNING: `--type={legacy_type}` is deprecated. '
            f'Use `ddev create {target} NAME` instead. The flag will be removed in a future release.',
            err=True,
        )

        # Strip the --type / -t flag out of args before handing back to click.
        cleaned = _strip_type_flag(args)
        return subcommand.name, subcommand, cleaned


def _extract_legacy_type(args: list[str]) -> str | None:
    """Return the `--type` / `-t` value from ``args`` if present, else None."""
    iterator = iter(enumerate(args))
    for _, token in iterator:
        if token == '--type' or token == '-t':
            try:
                _, value = next(iterator)
            except StopIteration:
                return None
            return value
        if token.startswith('--type='):
            return token.split('=', 1)[1]
        if token.startswith('-t=') or (token.startswith('-t') and len(token) > 2):
            return token[3:] if token.startswith('-t=') else token[2:]
    return None


def _strip_type_flag(args: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if token == '--type' or token == '-t':
            skip_next = True
            continue
        if token.startswith(('--type=', '-t=')) or (
            token.startswith('-t') and len(token) > 2 and not token.startswith('--')
        ):
            continue
        cleaned.append(token)
    return cleaned


@click.group(
    cls=_CreateGroup,
    short_help='Scaffold a new integration',
    context_settings={'help_option_names': ['-h', '--help']},
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
