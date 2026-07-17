# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Togo design-system theme."""

from rich.theme import Theme as RichTheme
from textual.theme import Theme

from ddev.cli.meta.ai.palette import (
    ACCENT,
    BACKGROUND,
    BORDER,
    ERROR,
    FOREGROUND,
    PANEL,
    PRIMARY,
    ROLE_GOAL_REVIEWER,
    ROLE_PHASE,
    SECONDARY,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    SUCCESS,
    SURFACE,
    TEXT_MUTED,
    WARNING,
)

togo_theme = Theme(
    name="togo",
    primary=PRIMARY,
    secondary=SECONDARY,
    accent=ACCENT,
    foreground=FOREGROUND,
    background=BACKGROUND,
    surface=SURFACE,
    panel=PANEL,
    success=SUCCESS,
    warning=WARNING,
    error=ERROR,
    dark=True,
    variables={
        "border": BORDER,
        "border-blurred": BORDER,
        "text-muted": TEXT_MUTED,
        "block-cursor-background": ACCENT,
        "block-cursor-foreground": BACKGROUND,
        "block-cursor-text-style": "bold",
        "footer-key-foreground": SECONDARY,
        "status-running": STATUS_RUNNING,
        "status-pending": STATUS_PENDING,
        "status-done": STATUS_DONE,
        "status-failed": STATUS_FAILED,
    },
)

# Rich's built-in Markdown element styles (``markdown.code``, ``markdown.block_quote``, etc.)
# default to fully saturated named colors (bright cyan, magenta, yellow) on a literal black
# background — agent responses and fetched docs render as Markdown, so those defaults show up
# directly in the log view regardless of the app's own theme. Push this over Rich's console
# theme so Markdown content stays inside the same muted palette as everything else.
togo_markdown_theme = RichTheme(
    {
        "markdown.code": f"bold {ROLE_PHASE} on {SURFACE}",
        "markdown.code_block": f"{ROLE_PHASE} on {SURFACE}",
        "markdown.block_quote": ROLE_GOAL_REVIEWER,
        "markdown.list": TEXT_MUTED,
        "markdown.item.bullet": f"bold {WARNING}",
        "markdown.item.number": f"bold {WARNING}",
        "markdown.hr": WARNING,
        "markdown.link": STATUS_RUNNING,
        "markdown.link_url": f"underline {STATUS_RUNNING}",
    }
)
