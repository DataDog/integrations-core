# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from typing import TypedDict

MAX_CHARS = 50_000
HEAD_RATIO = 0.6

ERROR_PATTERN = re.compile(r"ERROR|FAILED|Exception|Traceback|error:|fatal|panic", re.IGNORECASE)


class TruncationMeta(TypedDict):
    total_size: int
    shown_size: int
    truncated_size: int
    hint: str


def extract_error_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Return (index, line) pairs from lines matching error patterns."""
    return [(i, line) for i, line in enumerate(lines) if ERROR_PATTERN.search(line)]


def truncate(content: str, max_chars: int = MAX_CHARS) -> tuple[str, bool, TruncationMeta | None]:
    """Truncate content using error-aware head+tail strategy.

    Returns (output, truncated, meta).
    """
    if len(content) <= max_chars:
        return content, False, None

    total = len(content)
    gap_marker_approx = 100
    content_budget = max_chars - gap_marker_approx
    head_chars = int(content_budget * HEAD_RATIO)
    tail_chars = content_budget - head_chars

    head = content[:head_chars]
    tail = content[-tail_chars:]
    middle = content[head_chars : total - tail_chars]

    error_lines = extract_error_lines(middle.splitlines())

    if error_lines:
        error_snippet = "\n".join(line for _, line in error_lines)
        available = max_chars - len(error_snippet) - gap_marker_approx
        if available > 0:
            head_share = int(available * HEAD_RATIO)
            tail_share = available - head_share
            head = content[:head_share]
            tail = content[-tail_share:] if tail_share > 0 else ""
            removed = total - len(head) - len(error_snippet) - len(tail)
            gap = f"\n\n[... {removed} characters removed (errors preserved above) ...]\n\n"
            result = head + gap + error_snippet + "\n" + tail
        else:
            # error snippet alone is too large; fall back to plain split
            removed = total - head_chars - tail_chars
            gap = f"\n\n[... {removed} characters removed ...]\n\n"
            result = head + gap + tail
    else:
        removed = total - head_chars - tail_chars
        gap = f"\n\n[... {removed} characters removed ...]\n\n"
        result = head + gap + tail

    shown = len(result)
    meta: TruncationMeta = {
        "total_size": total,
        "shown_size": shown,
        "truncated_size": total - shown,
        "hint": f"Output truncated: showing {shown} of {total} characters.",
    }
    return result, True, meta
