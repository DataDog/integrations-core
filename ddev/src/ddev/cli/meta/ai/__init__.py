# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
``ddev meta ai`` command group.

Launches the Togo interface for browsing, configuring, running, and resuming
AI flows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


# The command name is set explicitly to `ai` so the function can be named `ai_group`,
# avoiding a clash with the `ddev.cli.meta.ai` package when imported into `ddev.cli.meta`.
@click.group('ai', short_help='Open the Togo AI flow interface', invoke_without_command=True)
@click.pass_context
def ai_group(ctx: click.Context) -> None:
    """Browse, configure, and run AI flows in Togo."""
    if ctx.invoked_subcommand is not None:
        return

    app: Application = ctx.obj

    from ddev.ai.agent.registry import build_agent_provider_registry
    from ddev.ai.config.engine import ConfigurationEngine
    from ddev.ai.config.errors import ConfigError
    from ddev.ai.constants import CORE_FLOWS_DIR, CORE_PHASES_DIR, CORE_PHASES_PACKAGE
    from ddev.ai.phases.registry import PhaseRegistry
    from ddev.cli.meta.ai.tui.app import TogoApp

    phase_registry = PhaseRegistry()
    phase_registry.register_from(CORE_PHASES_DIR, CORE_PHASES_PACKAGE)
    provider_registry = build_agent_provider_registry(app.config.ai)
    try:
        engine = ConfigurationEngine(
            core_dir=CORE_FLOWS_DIR,
            user_dirs=app.config.ai.flow_dirs,
            phase_registry=phase_registry,
            provider_registry=provider_registry,
        )
    except ConfigError as error:
        app.abort(str(error))

    togo = TogoApp(
        engine=engine,
        phase_registry=phase_registry,
        provider_registry=provider_registry,
        ddev_app=app,
    )
    httpx_logger = logging.getLogger('httpx')
    previous_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    try:
        togo.run()
    finally:
        httpx_logger.setLevel(previous_level)
