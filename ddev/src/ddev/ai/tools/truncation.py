# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from dataclasses import dataclass
from typing import Final

MAX_CHARS: Final = 50_000
HEAD_RATIO: Final = 0.6

ERROR_PATTERN = re.compile(r"ERROR|FAILED|Exception|Traceback|fatal|panic", re.IGNORECASE)


@dataclass
class TruncationMeta:
    total_size: int
    shown_size: int
    truncated_size: int
    hint: str


@dataclass
class TruncateResult:
    output: str
    truncated: bool
    meta: TruncationMeta | None


def extract_error_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Return (index, line) pairs from lines matching error patterns."""
    return [(i, line) for i, line in enumerate(lines) if ERROR_PATTERN.search(line)]


def truncate(
    content: str,
    max_chars: int = MAX_CHARS,
    head_ratio: float = HEAD_RATIO,
) -> TruncateResult:
    """Truncate content using error-aware head+tail strategy."""
    if len(content) <= max_chars:
        return TruncateResult(output=content, truncated=False, meta=None)

    total = len(content)
    gap_marker_approx = 100
    content_budget = max_chars - gap_marker_approx
    head_chars = int(content_budget * head_ratio)
    tail_chars = content_budget - head_chars

    head = content[:head_chars]
    tail = content[-tail_chars:]
    middle = content[head_chars : total - tail_chars]

    error_lines = extract_error_lines(middle.splitlines())

    errors_dropped = False
    if error_lines:
        error_snippet = "\n".join(line for _, line in error_lines)
        available = max_chars - len(error_snippet) - gap_marker_approx
        if available > 0:
            head_share = int(available * head_ratio)
            tail_share = available - head_share
            head = content[:head_share]
            tail = content[-tail_share:] if tail_share > 0 else ""
            removed = total - len(head) - len(error_snippet) - len(tail)
            gap = f"\n\n[... {removed} characters removed (errors preserved above) ...]\n\n"
            result = head + gap + error_snippet + "\n" + tail
        else:
            errors_dropped = True
            removed = total - head_chars - tail_chars
            gap = f"\n\n[... {removed} characters removed ...]\n\n"
            result = head + gap + tail
    else:
        removed = total - head_chars - tail_chars
        gap = f"\n\n[... {removed} characters removed ...]\n\n"
        result = head + gap + tail

    shown = len(result)
    if errors_dropped:
        hint = (
            f"Output truncated: showing {shown} of {total} characters. "
            f"Error lines were detected in the truncated region but could not be preserved "
            f"(error snippet exceeded the remaining budget)."
        )
    else:
        hint = f"Output truncated: showing {shown} of {total} characters."
    meta = TruncationMeta(
        total_size=total,
        shown_size=shown,
        truncated_size=total - shown,
        hint=hint,
    )
    return TruncateResult(output=result, truncated=True, meta=meta)
