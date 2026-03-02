from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


def _parse_time(ts: str | None, log: CheckLoggingAdapter | None = None) -> datetime | None:
    if not ts or ts == "null":
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        if log:
            log.error("Could not parse timestamp: %s", ts)
        return None
