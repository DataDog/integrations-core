# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Togo design-system color palette.

Single source of truth for every color used to render an AI flow run. The
Togo TUI delegates its Rich rendering and Textual theme to these constants
so neither reaches for arbitrary named colors outside this set.

All colors are deliberately muted/pastel rather than fully saturated: the
TUI log view is read at length against a dark background, and a fully
saturated palette reads as visually loud over long sessions.
"""

from __future__ import annotations

PRIMARY = "#8874C9"
SECONDARY = "#C3B5E8"
ACCENT = "#A38FD1"

FOREGROUND = "#E9E8EC"
BACKGROUND = "#17161C"
SURFACE = "#1D1C23"
PANEL = "#201F28"

BORDER = "#34323B"
TEXT_MUTED = "#8A8891"

SUCCESS = "#85C09A"
WARNING = "#E0B36A"
ERROR = "#E08A93"

STATUS_RUNNING = "#86B8DE"
STATUS_PENDING = "#8F8B94"
STATUS_DONE = SUCCESS
STATUS_FAILED = ERROR
STATUS_CONNECTOR = "#4A4650"

# Per-role identity colors used to tell speakers apart in the log.
ROLE_PHASE = "#7FC4C4"
ROLE_SUBAGENT = WARNING
ROLE_GOAL_REVIEWER = "#D99BB3"

# Tool-activity colors, distinct from role identity colors.
TOOL_CALL = WARNING
TOOL_SEARCH = "#A98FD9"
