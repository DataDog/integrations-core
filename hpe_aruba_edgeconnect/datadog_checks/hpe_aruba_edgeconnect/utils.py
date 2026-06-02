# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import Any

_SPEED_RE = re.compile(r'^(\d+)\s*(Mb/s|Gb/s|Kb/s)', re.IGNORECASE)

_SPEED_MULTIPLIERS = {
    'kb/s': 1_000,
    'mb/s': 1_000_000,
    'gb/s': 1_000_000_000,
}


def parse_speed(value: Any) -> float | None:
    """Parse interface speed to bits per second."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _SPEED_RE.match(str(value))
    if m:
        return float(m.group(1)) * _SPEED_MULTIPLIERS[m.group(2).lower()]
    return None
