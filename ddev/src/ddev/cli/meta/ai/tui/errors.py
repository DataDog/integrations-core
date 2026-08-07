# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shaping error text for single-line TUI surfaces such as banners and toasts."""

from __future__ import annotations

BANNER_ERROR_MAX_CHARS = 200


def compact_error_detail(error: str, max_chars: int = BANNER_ERROR_MAX_CHARS) -> str:
    """Reduce multi-line error text to one truncated line.

    Exception text is frequently multi-line: a YAML parse error carries the offending source and a
    caret, and a pydantic validation error one block per field. Banners and toasts have room for a
    single line, and anything appended after the raw text lands after the last line rather than
    after the message.

    Args:
        error: The error text to compact.
        max_chars: Maximum length of the returned line, including the ellipsis.
    """
    detail = next((line.strip() for line in error.splitlines() if line.strip()), error.strip())
    if len(detail) > max_chars:
        detail = f"{detail[: max_chars - 1].rstrip()}…"
    return detail
